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

from typing import ClassVar, Generic, TypeVar, cast

import paho.mqtt.client as mqtt
from pydantic import BaseModel, ConfigDict, model_validator

type ValidatorValues = dict[str, object]


class DeviceInfo(BaseModel):
    """Information about a device a sensor belongs to"""

    name: str
    model: str | None = None
    """The model name of the device."""
    model_id: str | None = None
    """The model identifier of the device."""
    manufacturer: str | None = None
    sw_version: str | None = None
    """Firmware version of the device"""
    hw_version: str | None = None
    """Hardware version of the device"""
    identifiers: list[str] | list[tuple[str, str]] | str | None = None
    """A list of IDs that uniquely identify the device. For example a serial number."""
    connections: list[tuple[str, str]] | None = None
    """A list of connections of the device to the outside world as a list of tuples        [connection_type, connection_identifier]"""
    configuration_url: str | None = None
    """A link to the webpage that can manage the configuration of this device.
        Can be either an HTTP or HTTPS link."""
    via_device: str | None = None
    """Identifier of a device that routes messages between this device and Home
        Assistant. Examples of such devices are hubs, or parent devices of a sub-device.
        This is used to show device topology in Home Assistant."""
    serial_number: str | None = None
    """The serial number of the device. Unlike a serial number in the identifiers set, this does not
    need to be unique."""
    suggested_area: str | None = None
    """The suggested name for the area where the device is located."""

    @model_validator(mode="before")
    @classmethod
    def must_have_identifiers_or_connection(cls, values: object) -> object:
        """Check that either `identifiers` or `connections` is set"""
        if not isinstance(values, dict):
            return values

        validator_values = cast(ValidatorValues, values)
        identifiers = validator_values.get("identifiers")
        connections = validator_values.get("connections")
        if identifiers is None and connections is None:
            raise ValueError("Define identifiers or connections")
        return validator_values


class EntityInfo(BaseModel):
    component: str
    """One of the supported MQTT components, for instance `binary_sensor`"""
    """Information about the sensor"""
    device: DeviceInfo | None = None
    """Information about the device this sensor belongs to"""
    device_class: str | None = None
    """Sets the class of the device, changing the device state and icon that is
        displayed on the frontend."""
    enabled_by_default: bool | None = None
    """Flag which defines if the entity should be enabled when first added."""
    entity_category: str | None = None
    """Classification of a non-primary entity."""
    expire_after: int | None = None
    """If set, it defines the number of seconds after the sensor’s state expires,
        if it’s not updated. After expiry, the sensor’s state becomes unavailable.
            Default the sensors state never expires."""
    force_update: bool | None = None
    """Sends update events even if the value hasn’t changed.    Useful if you want to have meaningful value graphs in history."""
    icon: str | None = None
    name: str
    """Name of the sensor inside Home Assistant"""
    object_id: str | None = None
    """Set this to generate the `entity_id` in HA instead of using `name`"""
    qos: int | None = None
    """The maximum QoS level to be used when receiving messages."""
    unique_id: str | None = None
    """Set this to enable editing sensor from the HA ui and to integrate with a
        device"""

    @model_validator(mode="before")
    @classmethod
    def device_need_unique_id(cls, values: object) -> object:
        """Check that `unique_id` is set if `device` is provided,            otherwise Home Assistant will not link the sensor to the device"""
        if not isinstance(values, dict):
            return values

        validator_values = cast(ValidatorValues, values)
        device = validator_values.get("device")
        unique_id = validator_values.get("unique_id")
        if device is not None and unique_id is None:
            raise ValueError("A unique_id is required if a device is defined")
        return validator_values


EntityType = TypeVar("EntityType", bound=EntityInfo)
UserDataT = TypeVar("UserDataT")


class Settings(BaseModel, Generic[EntityType]):
    class MQTT(BaseModel):
        """Connection settings for the MQTT broker"""

        model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

        host: str | None = "homeassistant"
        port: int | None = 1883
        username: str | None = None
        password: str | None = None
        client_name: str | None = None
        use_tls: bool | None = False
        tls_key: str | None = None
        tls_certfile: str | None = None
        tls_ca_cert: str | None = None

        discovery_prefix: str = "homeassistant"
        """The root of the topic tree where HA is listening for messages"""
        state_prefix: str = "hmd"
        """The root of the topic tree ha-mqtt-discovery publishes its state messages"""

        client: mqtt.Client | None = None
        """Optional MQTT client to use for the connection. If provided, most other settings are ignored."""

    mqtt: MQTT
    """Connection to MQTT broker"""
    entity: EntityType
    debug: bool = False
    """Print out the message that would be sent over MQTT"""
    manual_availability: bool = False
    """If true, the entity `availability` inside HA must be manually managed
    using the `set_availability()` method"""
