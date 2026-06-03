import asyncio

import aiomqtt
import pytest
from aiomqtt import Message

from ha_mqtt_discoverable import EntityInfo, MqttSession, Settings
from ha_mqtt_discoverable._base import Discoverable
from ha_mqtt_discoverable._topic_paths import build_status_topic


class DiscoverableHarness(Discoverable[EntityInfo]):
    pass


def test_session_exposes_config_prefixes_without_connecting() -> None:
    mqtt_settings = Settings.MQTT(
        host="localhost",
        client_name="test",
        discovery_prefix="custom_discovery",
        state_prefix="custom_state",
    )

    session = MqttSession(mqtt_settings)

    assert session.settings is mqtt_settings
    assert session.discovery_prefix == "custom_discovery"
    assert session.state_prefix == "custom_state"


def test_session_allows_multiple_entities() -> None:
    session = MqttSession(Settings.MQTT(host="localhost", client_name="test"))

    first = DiscoverableHarness(
        session,
        EntityInfo(name="first", component="binary_sensor"),
    )
    second = DiscoverableHarness(
        session,
        EntityInfo(name="second", component="binary_sensor"),
    )

    assert first.availability_topic == "hmd/binary_sensor/first/availability"
    assert second.availability_topic == "hmd/binary_sensor/second/availability"


def test_session_allows_availability_registration_after_connect() -> None:
    async def scenario() -> None:
        received = asyncio.Event()
        observed: dict[str, str] = {}

        async with MqttSession(
            Settings.MQTT(host="localhost", client_name="test")
        ) as session:

            async def callback(message: Message) -> None:
                observed["topic"] = str(message.topic)
                observed["payload"] = message.payload.decode("utf-8")
                received.set()

            entity = DiscoverableHarness(
                session,
                EntityInfo(name="connected", component="binary_sensor"),
            )
            session.subscribe(entity.availability_topic, callback)

            await entity.set_available(True)
            await asyncio.wait_for(received.wait(), timeout=2)

            assert observed == {
                "topic": entity.availability_topic,
                "payload": "online",
            }

    asyncio.run(scenario())


def test_session_dispatches_pre_registered_subscriptions() -> None:
    async def scenario() -> None:
        received = asyncio.Event()
        observed: dict[str, str] = {}
        topic = "hmd/session/test/command"

        async def callback(message: Message) -> None:
            observed["topic"] = str(message.topic)
            observed["payload"] = message.payload.decode("utf-8")
            received.set()

        session = MqttSession(Settings.MQTT(host="localhost", client_name="test"))
        session.subscribe(topic, callback)

        async with session:
            await session.publish(topic, "hello")
            await asyncio.wait_for(received.wait(), timeout=2)

        assert observed == {"topic": topic, "payload": "hello"}

    asyncio.run(scenario())


def test_session_failure_poisons_later_operations() -> None:
    async def scenario() -> None:
        started = asyncio.Event()
        topic = "hmd/session/failure/command"

        with pytest.raises(RuntimeError, match="boom"):
            async with MqttSession(
                Settings.MQTT(host="localhost", client_name="test")
            ) as session:

                async def callback(message: Message) -> None:
                    _ = message
                    started.set()
                    raise RuntimeError("boom")

                session.subscribe(topic, callback)
                await session.publish(topic, "hello")
                await asyncio.wait_for(started.wait(), timeout=2)
                await asyncio.sleep(0)
                await session.publish("hmd/session/failure/state", "after-failure")

    asyncio.run(scenario())


def test_session_dispatches_wildcard_subscription() -> None:
    async def scenario() -> None:
        received = asyncio.Event()
        observed: dict[str, str] = {}

        async def callback(message: Message) -> None:
            observed["topic"] = str(message.topic)
            observed["payload"] = message.payload.decode("utf-8")
            received.set()

        session = MqttSession(Settings.MQTT(host="localhost", client_name="test"))
        session.subscribe("hmd/session/wild/+", callback)

        async with session:
            await session.publish("hmd/session/wild/abc", "hello")
            await asyncio.wait_for(received.wait(), timeout=2)

        assert observed == {"topic": "hmd/session/wild/abc", "payload": "hello"}

    asyncio.run(scenario())


def test_callback_error_handler_handles_and_keeps_session_alive() -> None:
    async def scenario() -> None:
        handled = asyncio.Event()
        errors: list[str] = []
        topic = "hmd/session/handled/command"

        async def on_error(error: Exception, _message: Message) -> None:
            errors.append(str(error))
            handled.set()

        async def callback(_message: Message) -> None:
            raise RuntimeError("boom")

        async with MqttSession(
            Settings.MQTT(host="localhost", client_name="test"),
            on_callback_error=on_error,
        ) as session:
            session.subscribe(topic, callback)
            await session.publish(topic, "hello")
            await asyncio.wait_for(handled.wait(), timeout=2)
            # The handler returned cleanly, so the session is not poisoned and
            # later operations still succeed.
            await session.publish("hmd/session/handled/state", "after-handled")

        assert errors == ["boom"]

    asyncio.run(scenario())


def test_callback_error_handler_raising_poisons_session() -> None:
    async def scenario() -> None:
        started = asyncio.Event()
        topic = "hmd/session/reraise/command"

        async def on_error(_error: Exception, _message: Message) -> None:
            raise RuntimeError("handler-boom")

        async def callback(_message: Message) -> None:
            started.set()
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="handler-boom"):
            async with MqttSession(
                Settings.MQTT(host="localhost", client_name="test"),
                on_callback_error=on_error,
            ) as session:
                session.subscribe(topic, callback)
                await session.publish(topic, "hello")
                await asyncio.wait_for(started.wait(), timeout=2)
                await asyncio.sleep(0)
                await session.publish("hmd/session/reraise/state", "after-failure")

    asyncio.run(scenario())


def test_build_status_topic() -> None:
    assert build_status_topic("hmd", "proj1") == "hmd/proj1/status"
    assert build_status_topic("custom", "my-bridge") == "custom/my-bridge/status"


def test_session_publishes_retained_online_then_offline_on_status_topic() -> None:
    settings = Settings.MQTT(host="localhost", client_name="lifecycle-test")
    status_topic = build_status_topic(settings.state_prefix, settings.client_name)

    async def read_retained(topic: str) -> str | None:
        async with aiomqtt.Client("localhost") as observer:
            await observer.subscribe(topic)
            try:
                async with asyncio.timeout(2):
                    async for message in observer.messages:
                        assert message.retain is True
                        return message.payload.decode("utf-8")
            except TimeoutError:
                return None
        return None

    async def scenario() -> None:
        async with MqttSession(settings):
            # "online" is published (retained) during __aenter__
            assert await read_retained(status_topic) == "online"
        # graceful exit leaves a retained "offline"
        assert await read_retained(status_topic) == "offline"

    asyncio.run(scenario())
