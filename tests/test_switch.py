import asyncio

import pytest

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Switch, SwitchInfo
from ._session_stub import RecordingSession


async def noop_command_callback(_sender: Switch, _message: object) -> None:
    return None


@pytest.fixture
def switch() -> Switch:
    session = RecordingSession(Settings.MQTT(host="localhost", client_name="test"))
    return Switch(session, SwitchInfo(name="test"), noop_command_callback)


def test_required_config(switch: Switch):
    assert switch is not None


def test_change_state(switch: Switch):
    asyncio.run(switch.on())
    asyncio.run(switch.off())
