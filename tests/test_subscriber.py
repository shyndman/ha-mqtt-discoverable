import asyncio
from typing import cast

import pytest
from aiomqtt import Message

from ha_mqtt_discoverable import EntityInfo, MqttSession, Settings, Subscriber
from ._session_stub import RecordingSession


async def noop_command_callback(
    _sender: Subscriber[EntityInfo], _message: object
) -> None:
    return None


def command_topic(subscriber: Subscriber[EntityInfo]) -> str:
    topic = subscriber.generate_config()["command_topic"]
    assert isinstance(topic, str)
    return topic


def test_generate_config_includes_command_topic_when_callback_present():
    session = RecordingSession(Settings.MQTT(host="localhost", client_name="test"))
    subscriber = Subscriber(
        session,
        EntityInfo(name="test", component="button"),
        noop_command_callback,
    )

    config = subscriber.generate_config()

    assert config["command_topic"] == command_topic(subscriber)
    assert len(session.commands) == 1
    assert session.commands[0].topic == command_topic(subscriber)


def test_generate_config_omits_command_topic_without_callback():
    session = RecordingSession(Settings.MQTT(host="localhost", client_name="test"))
    subscriber = Subscriber(session, EntityInfo(name="test", component="button"))

    config = subscriber.generate_config()

    assert "command_topic" not in config
    assert session.commands == []


def test_command_callback_receives_sender_and_message():
    async def scenario() -> None:
        received = asyncio.Event()
        observed: dict[str, str] = {}

        async with MqttSession(
            Settings.MQTT(host="localhost", client_name="test")
        ) as session:
            subscriber: Subscriber[EntityInfo]

            async def callback(
                sender: Subscriber[EntityInfo],
                message: Message,
            ) -> None:
                observed["sender_name"] = cast(str, sender.generate_config()["name"])
                observed["payload"] = message.payload.decode()
                observed["topic"] = str(message.topic)
                received.set()

            subscriber = Subscriber(
                session,
                EntityInfo(name="test", component="button"),
                callback,
            )
            await session.publish(command_topic(subscriber), "on")
            await asyncio.wait_for(received.wait(), timeout=2)

            assert observed == {
                "sender_name": "test",
                "payload": "on",
                "topic": command_topic(subscriber),
            }

    asyncio.run(scenario())


def test_callback_failure_poisons_session():
    async def scenario() -> None:
        started = asyncio.Event()

        with pytest.raises(RuntimeError, match="boom"):
            async with MqttSession(
                Settings.MQTT(host="localhost", client_name="test")
            ) as session:

                async def callback(
                    _sender: Subscriber[EntityInfo],
                    _message: Message,
                ) -> None:
                    started.set()
                    raise RuntimeError("boom")

                subscriber = Subscriber(
                    session,
                    EntityInfo(name="test", component="button"),
                    callback,
                )
                await session.publish(command_topic(subscriber), "on")
                await asyncio.wait_for(started.wait(), timeout=2)
                await subscriber.write_config()

    asyncio.run(scenario())
