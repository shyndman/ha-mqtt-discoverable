import asyncio

import pytest

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Light, LightInfo
from ._session_stub import RecordingSession


async def noop_command_callback(_sender: Light, _message: object) -> None:
    return None


color_modes = ["rgb", "rgbw"]
effects = ["rainbow", "mycustomeffect"]


@pytest.fixture
def light() -> Light:
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    sensor_info = LightInfo(
        name="test",
        color_mode=True,
        supported_color_modes=color_modes,
        effect=True,
        effect_list=effects,
    )
    return Light(session, sensor_info, noop_command_callback)


def test_required_config():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    sensor = Light(session, LightInfo(name="test"), noop_command_callback)
    assert sensor is not None


def test_on_off(light: Light):
    asyncio.run(light.on())
    asyncio.run(light.off())


@pytest.mark.parametrize("brightness", [0, 255])
def test_brightness(light: Light, brightness: int):
    asyncio.run(light.brightness(brightness))


@pytest.mark.parametrize("brightness", [-1, 256])
def test_brightness_out_of_range(light: Light, brightness: int) -> None:
    with pytest.raises(RuntimeError):
        asyncio.run(light.brightness(brightness))


@pytest.mark.parametrize("color_mode", color_modes)
def test_color(light: Light, color_mode: str) -> None:
    asyncio.run(light.color(color_mode, {"test": 123}))


def test_color_unsupported(light: Light):
    with pytest.raises(RuntimeError):
        asyncio.run(light.color("test", {"r": 255, "g": 255, "b": 255}))


@pytest.mark.parametrize("effect", effects)
def test_effect(light: Light, effect: str) -> None:
    asyncio.run(light.effect(effect))


def test_effect_unsupported(light: Light):
    with pytest.raises(RuntimeError):
        asyncio.run(light.effect("unsupported_effect"))
