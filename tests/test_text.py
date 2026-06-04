import asyncio
import random
import string

import pytest

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Text, TextInfo
from ._session_stub import RecordingSession


async def noop_command_callback(_sender: Text, _message: object) -> None:
    return None


@pytest.fixture
def text() -> Text:
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    return Text(session, TextInfo(name="test", min=5), noop_command_callback)


def test_required_config():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    text = Text(session, TextInfo(name="test"), noop_command_callback)
    assert text is not None


def test_set_text(text: Text):
    asyncio.run(text.set_text("this is as test"))


def test_too_short_string(text: Text):
    with pytest.raises(RuntimeError):
        asyncio.run(text.set_text("t"))


def test_too_long_string(text: Text):
    letters = string.ascii_lowercase
    random_string = "".join(random.choice(letters) for _ in range(500))
    with pytest.raises(RuntimeError):
        asyncio.run(text.set_text(random_string))
