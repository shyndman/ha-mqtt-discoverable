#
#    Copyright 2022-2024 Joe Block <jpb@unixorn.net>
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
from __future__ import annotations

from collections.abc import Mapping
import json
from typing import override

from pydantic import Field

from ha_mqtt_discoverable._base import Subscriber
from ha_mqtt_discoverable._logging import get_logger
from ha_mqtt_discoverable._models import EntityInfo

logger = get_logger(__name__)


class SwitchInfo(EntityInfo):
    """Switch specific information"""

    component: str = "switch"
    optimistic: bool | None = None
    """Flag that defines if switch works in optimistic mode.
    Default: true if no state_topic defined, else false."""
    payload_off: str = "OFF"
    """The payload that represents off state. If specified, will be used for
    both comparing to the value in the state_topic (see value_template and
    state_off for details) and sending as off command to the command_topic"""
    payload_on: str = "ON"
    """The payload that represents on state. If specified, will be used for both
    comparing to the value in the state_topic (see value_template and state_on
    for details) and sending as on command to the command_topic."""
    retain: bool | None = None
    """If the published message should have the retain flag on or not"""
    state_topic: str | None = None
    """The MQTT topic subscribed to receive state updates."""


# Inherit the binary sensor payload semantics while keeping a single generic base.
class Switch(Subscriber[SwitchInfo]):
    """Implements an MQTT switch:
    https://www.home-assistant.io/integrations/switch.mqtt
    """

    async def off(self) -> None:
        """
        Set switch to off
        """
        logger.info(
            "setting switch state",
            entity=self._entity.name,
            state=self._entity.payload_off,
            topic=self.state_topic,
        )
        await self._state_helper(state=self._entity.payload_off)

    async def on(self) -> None:
        """
        Set switch to on
        """
        logger.info(
            "setting switch state",
            entity=self._entity.name,
            state=self._entity.payload_on,
            topic=self.state_topic,
        )
        await self._state_helper(state=self._entity.payload_on)


class LightInfo(EntityInfo):
    """Light specific information"""

    component: str = "light"

    state_schema: str = Field(
        default="json", alias="schema"
    )  # 'schema' is a reserved word by pydantic
    """Sets the schema of the state topic, ie the 'schema' field in the configuration"""
    optimistic: bool | None = None
    """Flag that defines if light works in optimistic mode.
    Default: true if no state_topic defined, else false."""
    payload_off: str = "OFF"
    """The payload that represents off state. If specified, will be used for
    both comparing to the value in the state_topic (see value_template and
    state_off for details) and sending as off command to the command_topic"""
    payload_on: str = "ON"
    """The payload that represents on state. If specified, will be used for both
    comparing to the value in the state_topic (see value_template and state_on
    for details) and sending as on command to the command_topic."""
    brightness: bool | None = False
    """Flag that defines if the light supports setting the brightness
    """
    color_mode: bool | None = None
    """Flag that defines if the light supports color mode"""
    supported_color_modes: list[str] | None = None
    """List of supported color modes. See
    https://www.home-assistant.io/integrations/light.mqtt/#supported_color_modes for current list of
    supported modes. Required if color_mode is set"""
    effect: bool | None = False
    """Flag that defines if the light supports effects"""
    effect_list: str | list[str] | None = None
    """List of supported effects. Required if effect is set"""
    retain: bool | None = True
    """If the published message should have the retain flag on or not"""
    state_topic: str | None = None
    """The MQTT topic subscribed to receive state updates."""


class Light(Subscriber[LightInfo]):
    """Implements an MQTT light.
    https://www.home-assistant.io/integrations/light.mqtt
    """

    async def on(self) -> None:
        """
        Set light to on
        """
        state_payload = {
            "state": self._entity.payload_on,
        }
        await self._update_json_state(state_payload)

    async def off(self) -> None:
        """
        Set light to off
        """
        state_payload = {
            "state": self._entity.payload_off,
        }
        await self._update_json_state(state_payload)

    async def brightness(self, brightness: int) -> None:
        """
        Set brightness of the light

        Args:
            brightness(int): Brightness value of [0,255]
        """
        if brightness < 0 or brightness > 255:
            raise RuntimeError(
                f"Brightness for light {self._entity.name} is out of range"
            )

        state_payload = {
            "brightness": brightness,
            "state": self._entity.payload_on,
        }

        await self._update_json_state(state_payload)

    async def color(self, color_mode: str, color: Mapping[str, object]) -> None:
        """
        Set color of the light.
        NOTE: Make sure color formatting conforms to color mode, it is up to the caller to make sure
        of this. Also, make sure the color mode is in the list supported_color_modes

        Args:
            color_mode(str): A valid color mode
            color(Dict[str, Any]): Color to set, according to color_mode format
        """
        if not self._entity.color_mode:
            raise RuntimeError(
                f"Light {self._entity.name} does not support setting color"
            )
        supported_color_modes = self._entity.supported_color_modes
        if supported_color_modes is None:
            raise RuntimeError(
                f"Light {self._entity.name} has no supported_color_modes configured"
            )
        if color_mode not in supported_color_modes:
            raise RuntimeError(
                f"Color is not in configured supported_color_modes {str(supported_color_modes)}"
            )
        # We do not check if color schema conforms to color mode formatting, it is up to the caller
        state_payload = {
            "color_mode": color_mode,
            "color": color,
            "state": self._entity.payload_on,
        }
        await self._update_json_state(state_payload)

    async def effect(self, effect: str) -> None:
        """
        Enable effect of the light

        Args:
            effect(str): Effect to apply
        """
        if not self._entity.effect:
            raise RuntimeError(f"Light {self._entity.name} does not support effects")
        effect_list = self._entity.effect_list
        if effect_list is None:
            raise RuntimeError(
                f"Light {self._entity.name} has no effect_list configured"
            )
        if effect not in effect_list:
            raise RuntimeError(
                f"Effect is not within configured effect_list {str(effect_list)}"
            )
        state_payload = {
            "effect": effect,
            "state": self._entity.payload_on,
        }
        await self._update_json_state(state_payload)

    async def _update_json_state(self, state: Mapping[str, object]) -> None:
        """
        Update MQTT sensor state

        Args:
            state(Dict[str, Any]): What state to set the light to
        """
        logger.info(
            "setting light state",
            entity=self._entity.name,
            state=state,
            topic=self.state_topic,
        )
        json_state = json.dumps(state)
        retain = True if self._entity.retain is None else self._entity.retain
        await self._state_helper(
            state=json_state, topic=self.state_topic, retain=retain
        )


class CoverInfo(EntityInfo):
    """Cover specific information"""

    component: str = "cover"

    optimistic: bool | None = None
    """Flag that defines if light works in optimistic mode.
    Default: true if no state_topic defined, else false."""
    payload_close: str = "CLOSE"
    """Command payload to close the cover"""
    payload_open: str = "OPEN"
    """Command payload to open the cover"""
    payload_stop: str = "STOP"
    """Command payload to open the cover"""
    position_closed: int = 0
    """Number which represents the fully closed position"""
    position_open: int = 100
    """Number which represents the fully open position"""
    state_open: str = "open"
    """Payload that represents open state"""
    state_opening: str = "opening"
    """Payload that represents opening state"""
    state_closed: str = "closed"
    """Payload that represents closed state"""
    state_closing: str = "closing"
    """Payload that represents closing state"""
    state_stopped: str = "stopped"
    """Payload that represents stopped state"""
    state_topic: str | None = None
    """The MQTT topic subscribed to receive state updates."""
    retain: bool | None = True
    """If the published message should have the retain flag on or not"""


class Cover(Subscriber[CoverInfo]):
    """Implements an MQTT cover:
    https://www.home-assistant.io/integrations/cover.mqtt
    """

    async def open(self) -> None:
        """Set cover state to open"""
        await self._update_state(self._entity.state_open)

    async def closed(self) -> None:
        """Set cover state to closed"""
        await self._update_state(self._entity.state_closed)

    async def closing(self) -> None:
        """Set cover state to closing"""
        await self._update_state(self._entity.state_closing)

    async def opening(self) -> None:
        """Set cover state to opening"""
        await self._update_state(self._entity.state_opening)

    async def stopped(self) -> None:
        """Set cover state to stopped"""
        await self._update_state(self._entity.state_stopped)

    @override
    async def _update_state(self, state: str | float | int | None) -> None:
        """
        Update MQTT sensor state

        Args:
            state(str): What state to set the cover to
        """
        logger.info(
            "setting cover state",
            entity=self._entity.name,
            state=state,
            topic=self.state_topic,
        )
        retain = True if self._entity.retain is None else self._entity.retain
        await self._state_helper(state=state, topic=self.state_topic, retain=retain)


class ButtonInfo(EntityInfo):
    """Button specific information"""

    component: str = "button"

    payload_press: str = "PRESS"
    """The payload to send to trigger the button."""
    retain: bool | None = None
    """If the published message should have the retain flag on or not"""


class Button(Subscriber[ButtonInfo]):
    """Implements an MQTT button:
    https://www.home-assistant.io/integrations/button.mqtt
    """


class TextInfo(EntityInfo):
    """Information about the `text` entity"""

    component: str = "text"

    max: int = 255
    """The maximum size of a text being set or received (maximum is 255)."""
    min: int = 0
    """The minimum size of a text being set or received."""
    mode: str | None = "text"
    """The mode off the text entity. Must be either text or password."""
    pattern: str | None = None
    """A valid regular expression the text being set or received must match with."""

    retain: bool | None = None
    """If the published message should have the retain flag on or not"""


class Text(Subscriber[TextInfo]):
    """Implements an MQTT text:
    https://www.home-assistant.io/integrations/text.mqtt/
    """

    async def set_text(self, text: str) -> None:
        """
        Update the text displayed by this sensor. Check that it is of acceptable length.

        Args:
            text(str): Value of the text configured for this entity
        """
        if not self._entity.min <= len(text) <= self._entity.max:
            bound = f"[{self._entity.min}, {self._entity.max}]"
            raise RuntimeError(
                f"Text is not within configured length boundaries {bound}"
            )

        logger.info(
            "setting text state",
            entity=self._entity.name,
            text=text,
            topic=self.state_topic,
        )
        await self._state_helper(str(text))


class NumberInfo(EntityInfo):
    """Information about the 'number' entity"""

    component: str = "number"

    max: float | int = 100
    """The maximum value of the number (defaults to 100)"""
    min: float | int = 1
    """The maximum value of the number (defaults to 1)"""
    mode: str | None = None
    """Control how the number should be displayed in the UI. Can be set to box
    or slider to force a display mode."""
    optimistic: bool | None = None
    """Flag that defines if switch works in optimistic mode.
    Default: true if no state_topic defined, else false."""
    payload_reset: str | None = None
    """A special payload that resets the state to None when received on the
    state_topic."""
    retain: bool | None = None
    """If the published message should have the retain flag on or not"""
    state_topic: str | None = None
    """The MQTT topic subscribed to receive state updates."""
    step: float | None = None
    """Step value. Smallest acceptable value is 0.001. Defaults to 1.0."""
    unit_of_measurement: str | None = None
    """Defines the unit of measurement of the sensor, if any. The
    unit_of_measurement can be null."""


class Number(Subscriber[NumberInfo]):
    """Implements an MQTT number:
    https://www.home-assistant.io/integrations/number.mqtt/
    """

    async def set_value(self, value: float) -> None:
        """
        Update the numeric value. Raises an error if not within the acceptable range.

        Args:
            value(str): Value of the number configured for this entity
        """
        if not self._entity.min <= value <= self._entity.max:
            bound = f"[{self._entity.min}, {self._entity.max}]"
            raise RuntimeError(f"Value is not within configured boundaries {bound}")

        logger.info(
            "setting number state",
            entity=self._entity.name,
            value=value,
            topic=self.state_topic,
        )
        await self._state_helper(value)


class SelectInfo(EntityInfo):
    """Switch specific information"""

    component: str = "select"
    optimistic: bool | None = None
    """Flag that defines if switch works in optimistic mode.
    Default: true if no state_topic defined, else false."""
    retain: bool | None = None
    """If the published message should have the retain flag on or not"""
    state_topic: str | None = None
    """The MQTT topic subscribed to receive state updates."""
    options: list[str] | None = None
    """List of options that can be selected. An empty list or a list with a single item is allowed."""


class Select(Subscriber[SelectInfo]):
    """
    Implements an MQTT select for Home Assistant MQTT discovery:
    https://www.home-assistant.io/integrations/select.mqtt/
    """

    async def set_options(self, opt: list[str]) -> None:
        """
        Update the selectable options.

        Args:
            opt (list): List of options that can be selected.
        """
        if not opt:
            raise RuntimeError("Image URL cannot be empty")

        logger.info(
            "publishing select options",
            entity=self._entity.name,
            options=opt,
            topic=self.state_topic,
        )
        await self._state_helper(json.dumps(opt))
