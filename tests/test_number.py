import asyncio

import pytest

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Number, NumberInfo
from ._session_stub import RecordingSession


async def noop_command_callback(_sender: Number, _message: object) -> None:
    return None


@pytest.fixture
def number() -> Number:
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    return Number(
        session, NumberInfo(name="test", min=5.0, max=90.0), noop_command_callback
    )


def test_required_config():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    number = Number(session, NumberInfo(name="test"), noop_command_callback)
    assert number is not None


def test_set_value(number: Number):
    asyncio.run(number.set_value(42.0))


def test_number_too_small(number: Number):
    with pytest.raises(RuntimeError):
        asyncio.run(number.set_value(4.0))


def test_number_too_large(number: Number):
    with pytest.raises(RuntimeError):
        asyncio.run(number.set_value(91.0))
