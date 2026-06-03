import asyncio

import pytest

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo
from ._session_stub import RecordingSession


@pytest.fixture(name="sensor")
def binary_sensor() -> BinarySensor:
    session = RecordingSession(Settings.MQTT(host="localhost", client_name="test"))
    sensor_info = BinarySensorInfo(name="test", payload_on="on")
    return BinarySensor(session, sensor_info)


def test_required_config(sensor: BinarySensor):
    assert sensor is not None


@pytest.mark.parametrize("payload_on", ["on", "custom_on"])
def test_generate_config(payload_on: str):
    session = RecordingSession(Settings.MQTT(host="localhost", client_name="test"))
    sensor = BinarySensor(session, BinarySensorInfo(name="test", payload_on=payload_on))

    config = sensor.generate_config()

    assert config["payload_on"] == payload_on


def test_update_state(sensor: BinarySensor):
    asyncio.run(sensor.on())
    asyncio.run(sensor.off())


def test_boolean_state(sensor: BinarySensor):
    asyncio.run(sensor.update_state(True))
    asyncio.run(sensor.update_state(False))
