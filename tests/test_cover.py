import asyncio

import pytest

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Cover, CoverInfo
from ._session_stub import RecordingSession


async def noop_command_callback(_sender: Cover, _message: object) -> None:
    return None


@pytest.fixture
def cover() -> Cover:
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    return Cover(session, CoverInfo(name="test"), noop_command_callback)


def test_required_config(cover: Cover):
    assert cover is not None


def test_open(cover: Cover):
    asyncio.run(cover.open())


def test_closed(cover: Cover):
    asyncio.run(cover.closed())


def test_closing(cover: Cover):
    asyncio.run(cover.closing())


def test_opening(cover: Cover):
    asyncio.run(cover.opening())


def test_stopped(cover: Cover):
    asyncio.run(cover.stopped())
