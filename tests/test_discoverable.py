import asyncio
import json
from typing import cast

import pytest

from ha_mqtt_discoverable import DeviceInfo, Discoverable, EntityInfo, Settings
from ._session_stub import RecordingSession


class DiscoverableHarness(Discoverable[EntityInfo]):
    async def publish_state(self, value: str | float | int | None) -> None:
        await self._state_helper(value)


def test_topics():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    entity = EntityInfo(name="test", component="binary_sensor")
    discoverable = DiscoverableHarness(session, entity)

    assert discoverable.config_topic == "homeassistant/binary_sensor/test/config"
    assert discoverable.state_topic == "hmd/binary_sensor/test/state"
    assert discoverable.attributes_topic == "hmd/binary_sensor/test/attributes"


def test_topics_with_device():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    entity = EntityInfo(
        name="test",
        component="binary_sensor",
        device=DeviceInfo(name="test_device", identifiers="id"),
        unique_id="unique_id",
    )
    discoverable = DiscoverableHarness(session, entity)

    assert (
        discoverable.config_topic
        == "homeassistant/binary_sensor/test_device/test/config"
    )
    assert discoverable.state_topic == "hmd/binary_sensor/test_device/test/state"
    assert (
        discoverable.attributes_topic == "hmd/binary_sensor/test_device/test/attributes"
    )


def test_generate_config():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    discoverable = DiscoverableHarness(
        session,
        EntityInfo(name="test", component="binary_sensor"),
    )

    config = discoverable.generate_config()

    assert config["name"] == "test"
    assert config["component"] == "binary_sensor"
    assert config["state_topic"] == discoverable.state_topic
    assert config["json_attributes_topic"] == discoverable.attributes_topic


def test_generate_config_connection_dependent_availability():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    discoverable = DiscoverableHarness(
        session,
        EntityInfo(name="test", component="binary_sensor"),
    )

    config = discoverable.generate_config()

    assert config["availability"] == [
        {"topic": session.status_topic},
        {"topic": "hmd/binary_sensor/test/availability"},
    ]
    assert config["availability_mode"] == "all"
    assert "availability_topic" not in config


def test_generate_config_connection_independent_availability():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    discoverable = DiscoverableHarness(
        session,
        EntityInfo(name="test", component="binary_sensor"),
        requires_connection=False,
    )

    config = discoverable.generate_config()

    assert config["availability_topic"] == "hmd/binary_sensor/test/availability"
    assert "availability" not in config
    assert "availability_mode" not in config


def test_multiple_entities_publish_distinct_availability_topics():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    first = DiscoverableHarness(
        session,
        EntityInfo(name="first", component="binary_sensor"),
    )
    second = DiscoverableHarness(
        session,
        EntityInfo(name="second", component="binary_sensor"),
    )

    asyncio.run(first.set_available(True))
    asyncio.run(second.set_available(False))

    availability_messages = [
        message
        for message in session.published
        if message.topic in {first.availability_topic, second.availability_topic}
    ]

    assert len(availability_messages) == 2
    assert availability_messages[0].topic == first.availability_topic
    assert availability_messages[0].payload == "online"
    assert availability_messages[1].topic == second.availability_topic
    assert availability_messages[1].payload == "offline"


def test_write_config_and_state_publish_retained():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    discoverable = DiscoverableHarness(
        session,
        EntityInfo(name="test", component="binary_sensor"),
    )

    asyncio.run(discoverable.publish_state("test"))

    assert discoverable.wrote_configuration is True
    by_topic = {message.topic: message for message in session.published}
    # config is written first, then the initial availability, then state
    assert by_topic[discoverable.config_topic].retain is True
    availability = by_topic[discoverable.availability_topic]
    assert availability.payload == "online"
    assert availability.retain is True
    state = by_topic[discoverable.state_topic]
    assert state.payload == "test"
    assert state.retain is True


def test_write_config_only_marks_success_after_publish() -> None:
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    discoverable = DiscoverableHarness(
        session,
        EntityInfo(name="test", component="binary_sensor"),
    )
    session.poison(RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(discoverable.write_config())

    assert discoverable.wrote_configuration is False
    assert session.published == []


def test_delete_publishes_empty_retained_config():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    discoverable = DiscoverableHarness(
        session,
        EntityInfo(name="test", component="binary_sensor"),
    )

    asyncio.run(discoverable.delete())

    assert len(session.published) == 1
    assert session.published[0].topic == discoverable.config_topic
    assert session.published[0].payload == ""
    assert session.published[0].retain is True


def test_set_attributes_publishes_json_payload():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    discoverable = DiscoverableHarness(
        session,
        EntityInfo(name="test", component="binary_sensor"),
    )

    asyncio.run(discoverable.set_attributes({"test attribute": "test"}))

    assert session.published[-1].topic == discoverable.attributes_topic
    payload = session.published[-1].payload
    assert isinstance(payload, str)
    assert cast(dict[str, object], json.loads(payload)) == {"test attribute": "test"}


def test_available_defaults_true_and_tracks_set_available():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    discoverable = DiscoverableHarness(
        session,
        EntityInfo(name="test", component="binary_sensor"),
    )

    assert discoverable.available is True

    asyncio.run(discoverable.set_available(False))
    assert discoverable.available is False

    asyncio.run(discoverable.set_available(True))
    assert discoverable.available is True


def test_set_available_publishes_online_and_offline():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    discoverable = DiscoverableHarness(
        session,
        EntityInfo(name="test", component="binary_sensor"),
    )

    asyncio.run(discoverable.set_available(True))
    asyncio.run(discoverable.set_available(False))

    assert [message.payload for message in session.published[-2:]] == [
        "online",
        "offline",
    ]
    assert all(
        message.topic == discoverable.availability_topic
        for message in session.published[-2:]
    )
