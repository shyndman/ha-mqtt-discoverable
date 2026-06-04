import pytest

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Button, ButtonInfo
from ._session_stub import RecordingSession


async def noop_command_callback(_sender: Button, _message: object) -> None:
    return None


@pytest.fixture(name="button")
def button() -> Button:
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    return Button(session, ButtonInfo(name="test"), noop_command_callback)


def test_required_config(button: Button):
    assert button is not None
    config = button.generate_config()
    assert "command_topic" in config
