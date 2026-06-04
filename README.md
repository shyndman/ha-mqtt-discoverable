# ha-mqtt-discoverable

[![License](https://img.shields.io/github/license/unixorn/ha-mqtt-discoverable.svg)](https://opensource.org/license/apache-2-0/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![GitHub last commit (branch)](https://img.shields.io/github/last-commit/unixorn/ha-mqtt-discoverable/main.svg)](https://github.com/unixorn/ha-mqtt-discoverable)
[![Downloads](https://static.pepy.tech/badge/ha-mqtt-discoverable)](https://pepy.tech/project/ha-mqtt-discoverable)

A Python 3 module that takes advantage of Home Assistant's [MQTT discovery protocol](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery) to create sensors without having to define anything on the HA side.

Using MQTT discoverable devices lets us add new sensors and devices to HA without having to restart HA. The [ha-mqtt-discoverable-cli](https://github.com/unixorn/ha-mqtt-discoverable-cli/) module includes scripts to make it easy to create discoverable devices from the command line if you don't want to bother writing Python.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
## Table of Contents

- [Installing](#installing)
  - [Python](#python)
- [Supported entities](#supported-entities)
  - [Binary sensor](#binary-sensor)
  - [Button](#button)
  - [Camera](#camera)
  - [Covers](#covers)
  - [Device](#device)
  - [Device trigger](#device-trigger)
  - [Image](#image)
  - [Light](#light)
  - [Media player](#media-player)
  - [Number](#number)
  - [Select](#select)
  - [Sensor](#sensor)
  - [Switch](#switch)
  - [Text](#text)
  - [Update](#update)
- [FAQ](#faq)
  - [I'm having problems on 32-bit ARM](#im-having-problems-on-32-bit-arm)
- [Contributing](#contributing)
- [Users of ha-mqtt-discoverable](#users-of-ha-mqtt-discoverable)
- [Contributors](#contributors)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Installing

### Python

ha-mqtt-discoverable runs on Python 3.13 or later.

`pip install ha-mqtt-discoverable` if you want to use it in your own python scripts. `pip install ha-mqtt-discoverable-cli` to install the `hmd` utility scripts.

All examples below use the async-native API:

```py
async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
    entity = SomeEntity(mqtt, SomeEntityInfo(...))
    await entity.write_config()
    await entity.set_state(...)
```

Broker URLs can carry the transport, username, password, host, port, and websocket path:

```py
Settings.MQTT(url="wss://user:password@broker.example:443/mqtt", client_name="my-project")
```

Supported schemes are `mqtt`, `mqtts`, `ws`, and `wss`. Default ports are 1883,
8883, 80, and 443 respectively. Paths are only valid for `ws` and `wss`.

<!-- Please keep the entities in alphabetical order -->
## Supported entities

The following Home Assistant entities are currently implemented:

- Binary sensor
- Button
- Camera
- Cover
- Device
- Device trigger
- Image
- Light
- Media player
- Number
- Select
- Sensor
- Switch
- Text
- Update

Each entity can be associated to a device. See below for details.

### Binary sensor

The following example creates a binary sensor and sets its state:

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo


async def main() -> None:
    sensor_info = BinarySensorInfo(name="MySensor", device_class="motion")

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        sensor = BinarySensor(mqtt, sensor_info)
        await sensor.on()
        await sensor.off()
        await sensor.update_state(True)
        await sensor.update_state(False)
        await sensor.set_attributes({"my attribute": "awesome"})
```

### Button

The button publishes no state; it only receives commands from HA.

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Button, ButtonInfo
from aiomqtt import Message


async def perform_my_custom_action() -> None:
    ...


async def on_press(_sender: Button, _message: Message) -> None:
    await perform_my_custom_action()


async def main() -> None:
    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        button = Button(mqtt, ButtonInfo(name="test"), on_press)
        await button.write_config()
```

### Camera

The following example creates a camera entity with a topic to a camera.

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Camera, CameraInfo
from aiomqtt import Message


async def on_camera_command(sender: Camera, message: Message) -> None:
    payload = message.payload.decode()
    await sender.set_topic(payload)


async def main() -> None:
    camera_info = CameraInfo(name="test", topic="zanzito/shared_locations/my-device")

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        camera = Camera(mqtt, camera_info, on_camera_command)
        await camera.set_topic("zanzito/shared_locations/my-device")
```

### Covers

A cover has five possible states `open`, `closed`, `opening`, `closing` and `stopped`.

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Cover, CoverInfo
from aiomqtt import Message


async def main() -> None:
    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        cover: Cover

        async def on_cover_command(sender: Cover, message: Message) -> None:
            payload = message.payload.decode()
            if payload == "OPEN":
                await sender.opening()
                open_my_custom_cover()
                await sender.open()
            elif payload == "CLOSE":
                await sender.closing()
                close_my_custom_cover()
                await sender.closed()
            elif payload == "STOP":
                stop_my_custom_cover()
                await sender.stopped()

        cover = Cover(mqtt, CoverInfo(name="test"), on_cover_command)
        await cover.closed()
```

### Device

From the [Home Assistant documentation](https://developers.home-assistant.io/docs/device_registry_index):
> A device is a special entity in Home Assistant that is represented by one or more entities.
A device is automatically created when an entity defines its `device` property.
A device will be matched up with an existing device via supplied identifiers or connections, like serial numbers or MAC addresses.

```py
from ha_mqtt_discoverable import DeviceInfo, MqttSession, Settings
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo


async def main() -> None:
    device_info = DeviceInfo(name="My device", identifiers="device_id")
    motion_sensor_info = BinarySensorInfo(
        name="My motion sensor",
        device_class="motion",
        unique_id="my_motion_sensor",
        device=device_info,
    )
    door_sensor_info = BinarySensorInfo(
        name="My door sensor",
        device_class="door",
        unique_id="my_door_sensor",
        device=device_info,
    )

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        motion_sensor = BinarySensor(mqtt, motion_sensor_info)
        door_sensor = BinarySensor(mqtt, door_sensor_info)
        await motion_sensor.on()
        await door_sensor.on()
```

### Device trigger

The following example creates a device trigger and generates a trigger event:

```py
from ha_mqtt_discoverable import DeviceInfo, MqttSession, Settings
from ha_mqtt_discoverable.sensors import DeviceTrigger, DeviceTriggerInfo


async def main() -> None:
    device_info = DeviceInfo(name="My device", identifiers="device_id")
    trigger_info = DeviceTriggerInfo(
        name="MyTrigger",
        type="button_press",
        subtype="button_1",
        unique_id="my_device_trigger",
        device=device_info,
    )

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        trigger = DeviceTrigger(mqtt, trigger_info)
        await trigger.trigger("My custom payload")
```

### Image

The following example creates an entity for an image URL.

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Image, ImageInfo


async def main() -> None:
    image_info = ImageInfo(name="test", url_topic="topic_to_publish_url_to")

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        image = Image(mqtt, image_info)
        await image.set_url("http://camera.local/latest.jpg")
```

### Light

The light payload is JSON-encoded and can both publish state and receive commands.

```py
import json

from aiomqtt import Message
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Light, LightInfo


async def main() -> None:
    light_info = LightInfo(
        name="test_light",
        brightness=True,
        color_mode=True,
        supported_color_modes=["rgb"],
        effect=True,
        effect_list=["blink", "my_custom_effect"],
    )

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        light: Light

        async def on_light_command(sender: Light, message: Message) -> None:
            payload = json.loads(message.payload.decode())
            if "color" in payload:
                set_color_of_my_light()
                await sender.color("rgb", payload["color"])
            elif "brightness" in payload:
                set_brightness_of_my_light()
                await sender.brightness(payload["brightness"])
            elif "effect" in payload:
                set_effect_of_my_light()
                await sender.effect(payload["effect"])
            elif payload.get("state") == light_info.payload_on:
                turn_on_my_light()
                await sender.on()
            elif payload.get("state") == light_info.payload_off:
                turn_off_my_light()
                await sender.off()

        light = Light(mqtt, light_info, on_light_command)
        await light.off()
```

### Media player

The media player publishes playback state and metadata, and only emits command topics for callbacks you provide.

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.media_player import MediaPlayer, MediaPlayerInfo
from aiomqtt import Message


async def main() -> None:
    media_player_info = MediaPlayerInfo(
        name="living_room_player",
        device_class="speaker",
        source_list=["tv", "bluetooth"],
    )

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        player: MediaPlayer

        async def play(sender: MediaPlayer, _message: Message) -> None:
            start_playback()
            await sender.set_state("playing")

        async def volume_set(sender: MediaPlayer, volume: float, _message: Message) -> None:
            set_device_volume(volume)
            await sender.set_volume(volume)

        player = MediaPlayer(
            mqtt,
            media_player_info,
            {"play": play, "volume_set": volume_set},
        )

        await player.write_config()
        await player.set_state("playing")
        await player.set_title("Song Title")
        await player.set_artist("Artist Name")
        await player.set_volume(0.4)
```

### Number

The number entity is similar to the text entity, but for numeric values.

```py
import logging

from aiomqtt import Message
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Number, NumberInfo


async def main() -> None:
    number_info = NumberInfo(name="test", min=0, max=50, mode="slider", step=5)

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        number: Number

        async def on_number(sender: Number, message: Message) -> None:
            value = float(message.payload.decode())
            logging.info("Received %s from HA", value)
            do_some_custom_thing(value)
            await sender.set_value(value)

        number = Number(mqtt, number_info, on_number)
        await number.set_value(42.0)
```

### Select

The selection entity is a list of selectable options in Home Assistant.

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Select, SelectInfo
from aiomqtt import Message


async def main() -> None:
    select_info = SelectInfo(name="test", options=["option1", "option2", "option3"])

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        async def on_select(sender: Select, message: Message) -> None:
            payload = message.payload.decode()
            do_something(payload)
            await sender.set_options([payload, "option4", "option5"])

        selection = Select(mqtt, select_info, on_select)
        await selection.set_options(["option3", "option4", "option5"])
```

### Sensor

The following example creates a sensor and sets its state:

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Sensor, SensorInfo


async def main() -> None:
    sensor_info = SensorInfo(
        name="MyTemperatureSensor",
        device_class="temperature",
        unit_of_measurement="°C",
    )

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        sensor = Sensor(mqtt, sensor_info)
        await sensor.set_state(20.5)
```

### Switch

The switch is similar to a binary sensor, but it also receives commands from HA.

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Switch, SwitchInfo
from aiomqtt import Message


async def main() -> None:
    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        switch: Switch

        async def on_switch(sender: Switch, message: Message) -> None:
            payload = message.payload.decode()
            if payload == "ON":
                turn_my_custom_thing_on()
                await sender.on()
            elif payload == "OFF":
                turn_my_custom_thing_off()
                await sender.off()

        switch = Switch(mqtt, SwitchInfo(name="test"), on_switch)
        await switch.off()
```

### Text

The text entity shows an input field in the HA UI.

```py
import logging

from aiomqtt import Message
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Text, TextInfo


async def main() -> None:
    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        async def on_text(sender: Text, message: Message) -> None:
            text = message.payload.decode()
            logging.info("Received %s from HA", text)
            do_some_custom_thing(text)
            await sender.set_text(text)

        text = Text(mqtt, TextInfo(name="test"), on_text)
        await text.set_text("Some awesome text")
```

### Update

The update entity tracks software or firmware updates and optionally receives install commands.

```py
from ha_mqtt_discoverable import MqttSession, Settings
from ha_mqtt_discoverable.sensors import Update, UpdateInfo
from aiomqtt import Message


async def main() -> None:
    update_info = UpdateInfo(
        name="my-software",
        device_class="firmware",
        title="My Software",
        release_summary="Bug fixes and improvements",
        release_url="https://github.com/myproject/releases",
    )

    async with MqttSession(Settings.MQTT(url="mqtt://localhost", client_name="my-project")) as mqtt:
        update: Update

        async def install(sender: Update, message: Message) -> None:
            if message.payload.decode() != update_info.payload_install:
                return
            start_my_update_process()
            await sender.set_progress(25)
            continue_update_process()
            await sender.set_progress(75)
            finalize_update_process()
            await sender.set_state(installed="1.2.3", latest="1.2.3")

        update = Update(mqtt, update_info, install)
        await update.set_state(installed="1.2.2", latest="1.2.3")
```

## FAQ

### I'm having problems on 32-bit ARM

Pydantic 2 has issues on 32-bit ARM. More details are on [ha-mqtt-discoverable/pull/191](https://github.com/unixorn/ha-mqtt-discoverable/pull/191). TL;DR: If you're on an ARM32 machine you're going to have to pin to the 0.13.1 version.

## Contributing

Run `task test` to execute the test suite. It starts a temporary Mosquitto broker, runs `pytest`, then shuts the broker down.

Run `task format` before submitting. There are `git` hooks already configured to run `ruff` and other checks before every commit, please run `prek install` to enable them.

## Users of ha-mqtt-discoverable

If you use this module for your own project, please add a link here.

- [ha-mqtt-discoverable-cli](https://github.com/unixorn/ha-mqtt-discoverable-cli) - Command line tools that allow using this module from shell scripts

- [plejd-mqtt-ha](https://github.com/ha-enthus1ast/plejd-mqtt-ha) - A containerized Python application that bridges Plejd devices to Home Assistant

- [homeassistant-zodiac-tri-expert](https://github.com/andreondra/homeassistant-zodiac-tri-expert) - A Zodiac Tri Expert salt water generator integration

- [homeassistant-addon-viessmann-gridbox](https://github.com/unl0ck/homeassistant-addon-viessmann-gridbox) - Get your Viessmann Gridbox Data Home Assistant integration

## Contributors

[![Contributors](https://contributors-img.web.app/image?repo=unixorn/ha-mqtt-discoverable)](https://github.com/unixorn/ha-mqtt-discoverable/graphs/contributors)

Made with [contributors-img](https://contributors-img.web.app).
