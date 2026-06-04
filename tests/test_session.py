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
        url="mqtt://localhost",
        client_name="test",
        discovery_prefix="custom_discovery",
        state_prefix="custom_state",
    )

    session = MqttSession(mqtt_settings)

    assert session.settings is mqtt_settings
    assert session.discovery_prefix == "custom_discovery"
    assert session.state_prefix == "custom_state"


def test_session_allows_multiple_entities() -> None:
    session = MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="test"))

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
            Settings.MQTT(url="mqtt://localhost", client_name="test")
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

        session = MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="test"))
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
                Settings.MQTT(url="mqtt://localhost", client_name="test")
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

        session = MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="test"))
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
            Settings.MQTT(url="mqtt://localhost", client_name="test"),
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
                Settings.MQTT(url="mqtt://localhost", client_name="test"),
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


def test_transport_defaults_to_tcp() -> None:
    settings = Settings.MQTT(url="mqtt://localhost", client_name="test")
    assert settings.transport == "tcp"
    assert settings.websocket_path is None
    assert settings.websocket_headers is None


@pytest.mark.parametrize("legacy_arg", ["host", "port", "use_tls"])
def test_mqtt_url_replaces_legacy_connection_params(legacy_arg: str) -> None:
    with pytest.raises(ValueError):
        Settings.MQTT.model_validate(
            {"url": "mqtt://localhost", "client_name": "test", legacy_arg: "unused"}
        )


@pytest.mark.parametrize(
    ("url", "host", "port", "transport", "websocket_path", "use_tls"),
    [
        ("mqtt://mqtt.example", "mqtt.example", 1883, "tcp", None, False),
        ("mqtts://mqtt.example", "mqtt.example", 8883, "tcp", None, True),
        ("ws://mqtt.example", "mqtt.example", 80, "websockets", None, False),
        ("wss://mqtt.example/mqtt", "mqtt.example", 443, "websockets", "/mqtt", True),
        (
            "wss://mqtt.example:8443/mqtt",
            "mqtt.example",
            8443,
            "websockets",
            "/mqtt",
            True,
        ),
    ],
)
def test_mqtt_url_derives_connection_settings(
    url: str,
    host: str,
    port: int,
    transport: str,
    websocket_path: str | None,
    use_tls: bool,
) -> None:
    settings = Settings.MQTT(url=url, client_name="test")

    assert settings.host == host
    assert settings.port == port
    assert settings.transport == transport
    assert settings.websocket_path == websocket_path
    assert settings.use_tls is use_tls


@pytest.mark.parametrize("url", ["mqtt://mqtt.example/mqtt", "mqtts://mqtt.example/"])
def test_mqtt_url_rejects_paths_for_tcp_schemes(url: str) -> None:
    with pytest.raises(ValueError, match="paths are only valid"):
        Settings.MQTT(url=url, client_name="test")


@pytest.mark.parametrize(
    "url", ["http://mqtt.example", "mqtt://", "wss://mqtt.example/mqtt?x=1"]
)
def test_mqtt_url_rejects_invalid_urls(url: str) -> None:
    with pytest.raises(ValueError):
        Settings.MQTT(url=url, client_name="test")


def test_session_forwards_websocket_settings_to_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _StopConnect(Exception):
        pass

    class _CapturingClient:
        def __init__(self, host: str, **kwargs: object) -> None:
            captured["host"] = host
            captured.update(kwargs)

        async def __aenter__(self) -> "_CapturingClient":
            raise _StopConnect

        async def __aexit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(aiomqtt, "Client", _CapturingClient)

    settings = Settings.MQTT(
        client_name="ws-test",
        url="wss://broker:8443/mqtt",
        websocket_headers={"Authorization": "Bearer token"},
    )

    async def scenario() -> None:
        with pytest.raises(_StopConnect):
            async with MqttSession(settings):
                pass

    asyncio.run(scenario())

    assert captured["host"] == "broker"
    assert captured["port"] == 8443
    assert captured["transport"] == "websockets"
    assert captured["websocket_path"] == "/mqtt"
    assert captured["websocket_headers"] == {"Authorization": "Bearer token"}


def test_session_publishes_retained_online_then_offline_on_status_topic() -> None:
    settings = Settings.MQTT(url="mqtt://localhost", client_name="lifecycle-test")
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
