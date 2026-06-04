import asyncio

import pytest

from ha_mqtt_discoverable import DeviceInfo, Settings
from ha_mqtt_discoverable.sensors import DeviceTrigger, DeviceTriggerInfo
from ._session_stub import RecordingSession


@pytest.fixture(name="device_trigger")
def device_trigger() -> DeviceTrigger:
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    device_info = DeviceInfo(name="test", identifiers="id")
    sensor_info = DeviceTriggerInfo(
        name="test",
        device=device_info,
        type="button_press",
        subtype="button_1",
        unique_id="test",
    )
    return DeviceTrigger(session, sensor_info)


def test_required_config(device_trigger: DeviceTrigger):
    assert device_trigger is not None


def test_config_topic(device_trigger: DeviceTrigger):
    config = device_trigger.generate_config()
    assert config["topic"] == device_trigger.state_topic


def test_trigger(device_trigger: DeviceTrigger):
    asyncio.run(device_trigger.trigger("my_payload"))
