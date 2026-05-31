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

import logging
from typing import Annotated

from pydantic import Field

from ha_mqtt_discoverable._base import Discoverable
from ha_mqtt_discoverable._models import EntityInfo

logger = logging.getLogger(__name__)


class BinarySensorInfo(EntityInfo):
    """Binary sensor specific information"""

    component: str = "binary_sensor"
    off_delay: int | None = None
    """For sensors that only send on state updates (like PIRs), this variable
    sets a delay in seconds after which the sensor's state will be updated back
    to off."""
    payload_off: str = "off"
    """Payload to send for the ON state"""
    payload_on: str = "on"
    """Payload to send for the OFF state"""


class BinarySensor(Discoverable[BinarySensorInfo]):
    def off(self):
        """
        Set binary sensor to off
        """
        self.update_state(state=False)

    def on(self):
        """
        Set binary sensor to on
        """
        self.update_state(state=True)

    def update_state(self, state: bool) -> None:
        """
        Update MQTT sensor state

        Args:
            state(bool): What state to set the sensor to
        """
        state_message = self._entity.payload_on if state else self._entity.payload_off
        logger.info(
            f"Setting {self._entity.name} to {state_message} using {self.state_topic}"
        )
        self._state_helper(state=state_message)


class SensorInfo(EntityInfo):
    """Sensor specific information"""

    component: str = "sensor"
    unit_of_measurement: str | None = None
    """Defines the units of measurement of the sensor, if any."""
    state_class: str | None = None
    """Defines the type of state.
    If not None, the sensor is assumed to be numerical
    and will be displayed as a line-chart
    in the frontend instead of as discrete values."""
    value_template: str | None = None
    """
    Defines a template to extract the value.
    If the template throws an error,
    the current state will be used instead."""
    last_reset_value_template: str | None = None
    """
    Defines a template to extract the last_reset.
    When last_reset_value_template is set, the state_class option must be total.
    Available variables: entity_id.
    The entity_id can be used to reference the entity’s attributes."""
    suggested_display_precision: None | Annotated[int, Field(ge=0)] = None
    """
    The number of decimals which should be used in the sensor’s state after rounding.
    """


class Sensor(Discoverable[SensorInfo]):
    def set_state(
        self, state: str | int | float, last_reset: str | None = None
    ) -> None:
        """
        Update the sensor state

        Args:
            state(str): What state to set the sensor to
            last_reset(str): ISO 8601-formatted string when an accumulating sensor was initialized
        """
        logger.info(f"Setting {self._entity.name} to {state} using {self.state_topic}")
        if last_reset:
            logger.info("Setting last_reset to " + last_reset)
        self._state_helper(str(state), last_reset=last_reset)
