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

import json
import logging
import ssl
from collections.abc import Callable
from importlib import metadata
from typing import ClassVar, Generic, Protocol, TypeVar, cast, override

import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessageInfo
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode
from pydantic import BaseModel, ConfigDict, model_validator

from ha_mqtt_discoverable._config import (
    CONFIGURATION_KEY_NAMES as _CONFIGURATION_KEY_NAMES,
)

# Read version from the package metadata
__version__ = metadata.version(cast(str, __package__))

logger = logging.getLogger(__name__)


type ValidatorValues = dict[str, object]
type OnConnectCallback = Callable[..., None]
type MessageCallback[UserDataT] = Callable[
    [mqtt.Client, UserDataT | None, mqtt.MQTTMessage], None
]


class TlsSetFunction(Protocol):
    def __call__(
        self,
        ca_certs: str | None = None,
        certfile: str | None = None,
        keyfile: str | None = None,
        cert_reqs: ssl.VerifyMode | None = None,
        tls_version: int | None = None,
        ciphers: str | None = None,
        keyfile_password: str | None = None,
        alpn_protocols: list[str] | None = None,
    ) -> None: ...


CONFIGURATION_KEY_NAMES = _CONFIGURATION_KEY_NAMES


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
    """A list of connections of the device to the outside world as a list of tuples\
        [connection_type, connection_identifier]"""
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
    """Sends update events even if the value hasn’t changed.\
    Useful if you want to have meaningful value graphs in history."""
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
        """Check that `unique_id` is set if `device` is provided,\
            otherwise Home Assistant will not link the sensor to the device"""
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

        # To use mqtt.Client
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


class Discoverable(Generic[EntityType]):
    """
    Base class for making MQTT discoverable objects
    """

    _settings: Settings[EntityType]
    _entity: EntityType

    mqtt_client: mqtt.Client
    wrote_configuration: bool = False
    debug: bool = False
    config_message: str = ""
    # MQTT topics
    _entity_topic: str
    config_topic: str
    state_topic: str
    availability_topic: str
    attributes_topic: str

    def __init__(
        self,
        settings: Settings[EntityType],
        on_connect: OnConnectCallback | None = None,
    ) -> None:
        """
        Creates a basic discoverable object.

        Args:
            settings: Settings for the entity we want to create in Home Assistant.
            See the `Settings` class for the available options.
            on_connect: Optional callback function invoked when the MQTT client \
                successfully connects to the broker.
            If defined, you need to call `_connect_client()` to establish the \
                connection manually.
        """
        # Import here to avoid circular dependency on imports
        # TODO how to better handle this?
        from ha_mqtt_discoverable.utils import clean_string

        self._settings = settings
        self._entity = settings.entity

        entity_topic_basename = clean_string(
            self._entity.object_id
            if self._entity.object_id is not None
            else self._entity.name
        )

        # Build the topic string: start from the type of component
        # e.g. `binary_sensor`
        self._entity_topic = f"{self._entity.component}"
        # If present, append the device name, e.g. `binary_sensor/mydevice`
        self._entity_topic += (
            f"/{clean_string(self._entity.device.name)}" if self._entity.device else ""
        )
        # Append the sensor name, e.g. `binary_sensor/mydevice/mysensor`
        self._entity_topic += f"/{entity_topic_basename}"

        # Full topic where we publish the configuration message to be picked up by HA
        # Prepend the `discovery_prefix`, default: `homeassistant`
        # e.g. homeassistant/binary_sensor/mydevice/mysensor
        self.config_topic = (
            f"{self._settings.mqtt.discovery_prefix}/{self._entity_topic}/config"
        )
        # Full topic where we publish our own state messages
        # Prepend the `state_prefix`, default: `hmd`
        # e.g. hmd/binary_sensor/mydevice/mysensor
        self.state_topic = (
            f"{self._settings.mqtt.state_prefix}/{self._entity_topic}/state"
        )

        # Full topic where we publish our own attributes as JSON messages
        # Prepend the `state_prefix`, default: `hmd`
        # e.g. hmd/binary_sensor/mydevice/mysensor
        self.attributes_topic = (
            f"{self._settings.mqtt.state_prefix}/{self._entity_topic}/attributes"
        )

        logger.info(f"config_topic: {self.config_topic}")
        logger.info(f"state_topic: {self.state_topic}")
        if self._settings.manual_availability:
            # Define the availability topic, using `hmd` topic prefix
            self.availability_topic = (
                f"{self._settings.mqtt.state_prefix}/{self._entity_topic}/availability"
            )
            logger.debug(f"availability_topic: {self.availability_topic}")

        # Create the MQTT client, registering the user `on_connect` callback
        self._setup_client(on_connect)
        # If there is a callback function defined, the user must manually connect
        # to the MQTT client
        if not (on_connect or self._settings.mqtt.client is not None):
            self._connect_client()

    @override
    def __str__(self) -> str:
        """
        Generate a string representation of the Discoverable object
        """
        dump = f"""
settings: {self._settings}
topic_prefix: {self._entity_topic}
config_topic: {self.config_topic}
state_topic: {self.state_topic}
wrote_configuration: {self.wrote_configuration}
        """
        return dump

    def _setup_client(self, on_connect: OnConnectCallback | None = None) -> None:
        """Create an MQTT client and setup some basic properties on it"""

        # If the user has passed in an MQTT client, use it
        if self._settings.mqtt.client:
            self.mqtt_client = self._settings.mqtt.client
            return

        mqtt_settings = self._settings.mqtt
        logger.debug(
            f"Creating mqtt client ({mqtt_settings.client_name}) for {mqtt_settings.host}:{mqtt_settings.port}"
        )
        self.mqtt_client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=mqtt_settings.client_name,
        )
        tls_set = cast(TlsSetFunction, self.mqtt_client.tls_set)
        if mqtt_settings.tls_key:
            logger.info(
                f"Connecting to {mqtt_settings.host}:{mqtt_settings.port} with SSL and client certificate authentication"
            )
            logger.debug(f"ca_certs={mqtt_settings.tls_ca_cert}")
            logger.debug(f"certfile={mqtt_settings.tls_certfile}")
            logger.debug(f"keyfile={mqtt_settings.tls_key}")
            tls_set(
                ca_certs=mqtt_settings.tls_ca_cert,
                certfile=mqtt_settings.tls_certfile,
                keyfile=mqtt_settings.tls_key,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
            )
        elif mqtt_settings.use_tls:
            logger.info(
                f"Connecting to {mqtt_settings.host}:{mqtt_settings.port} with SSL and username/password authentication"
            )
            logger.debug(f"ca_certs={mqtt_settings.tls_ca_cert}")
            if mqtt_settings.tls_ca_cert:
                tls_set(
                    ca_certs=mqtt_settings.tls_ca_cert,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS,
                )
            else:
                tls_set(
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS,
                )
            if mqtt_settings.username:
                self.mqtt_client.username_pw_set(
                    mqtt_settings.username, password=mqtt_settings.password
                )
        else:
            logger.debug(
                f"Connecting to {mqtt_settings.host}:{mqtt_settings.port} without SSL"
            )
            if mqtt_settings.username:
                self.mqtt_client.username_pw_set(
                    mqtt_settings.username, password=mqtt_settings.password
                )
        if on_connect:
            logger.debug("Registering custom callback function")
            self.mqtt_client.on_connect = on_connect

        if self._settings.manual_availability:
            self.mqtt_client.will_set(self.availability_topic, "offline", retain=True)

    def _connect_client(self) -> None:
        """Connect the client to the MQTT broker, start its onw internal loop in
        a separate thread"""
        host = cast(str, self._settings.mqtt.host)
        port = self._settings.mqtt.port or 1883
        logger.debug(f"Connecting MQTT client to broker at {host}:{port}")

        result = self.mqtt_client.connect(host, port)
        # Check if we have established a connection
        if result != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                f"Failed to connect to MQTT broker at {host}:{port}, error code: {result}"
            )
            raise RuntimeError("Error while connecting to MQTT broker")

        logger.debug(f"Successfully connected to MQTT broker at {host}:{port}")

        # Start the internal network loop of the MQTT library to handle incoming
        # messages in a separate thread
        logger.debug("Starting MQTT client loop in separate thread")
        self.mqtt_client.loop_start()
        logger.debug("MQTT client loop started successfully")

    def _state_helper(
        self,
        state: str | float | int | None,
        topic: str | None = None,
        last_reset: str | None = None,
        retain: bool = True,
    ) -> MQTTMessageInfo | None:
        """
        Write a state to the given MQTT topic, returning the result of client.publish()
        """
        if not self.wrote_configuration:
            logger.debug("Writing sensor configuration")
            _ = self.write_config()
        if not topic:
            logger.debug(f"State topic unset, using default: {self.state_topic}")
            topic = self.state_topic
        if last_reset:
            state = json.dumps({"state": state, "last_reset": last_reset})
        logger.debug(f"Writing '{state}' to {topic}")

        if self._settings.debug:
            logger.debug(f"Debug is {self.debug}, skipping state write")
            return

        message_info = self.mqtt_client.publish(topic, state, retain=retain)
        logger.debug(f"Publish result: {message_info}")
        return message_info

    def debug_mode(self, mode: bool) -> None:
        self.debug = mode
        logger.debug(f"Set debug mode to {self.debug}")

    def delete(self) -> MQTTMessageInfo:
        """
        Delete a synthetic sensor from Home Assistant via MQTT message.

        Based on https://www.home-assistant.io/docs/mqtt/discovery/

        mosquitto_pub -r -h 127.0.0.1 -p 1883 \
            -t "homeassistant/binary_sensor/garden/config" \
            -m '{"name": "garden", "device_class": "motion", \
            "state_topic": "homeassistant/binary_sensor/garden/state"}'
        """

        config_message = ""
        logger.info(
            f"Writing '{config_message}' to topic {self.config_topic} on {self._settings.mqtt.host}:{self._settings.mqtt.port}"
        )
        return self.mqtt_client.publish(self.config_topic, config_message, retain=True)

    def generate_config(self) -> dict[str, object]:
        """
        Generate a dictionary that we'll grind into JSON and write to MQTT.

        Will be used with the MQTT discovery protocol to make Home Assistant
        automagically ingest the new sensor.
        """
        # Automatically generate a dict using pydantic
        # Exclude object_id since we transform it to default_entity_id
        config = cast(
            dict[str, object],
            self._entity.model_dump(exclude_none=True, exclude={"object_id"}),
        )

        # Transform object_id to default_entity_id (HA 2025.x deprecation fix)
        # Format: "{component}.{object_id}" e.g. "media_player.mock_player"
        if self._entity.object_id:
            config["default_entity_id"] = (
                f"{self._entity.component}.{self._entity.object_id}"
            )

        # Add the MQTT topics to be discovered by HA
        topics = {
            "state_topic": self.state_topic,
            "json_attributes_topic": self.attributes_topic,
        }
        # Add availability topic if defined
        if hasattr(self, "availability_topic"):
            topics["availability_topic"] = self.availability_topic
        return config | topics

    def write_config(self):
        """
        mosquitto_pub -r -h 127.0.0.1 -p 1883 \
            -t "homeassistant/binary_sensor/garden/config" \
            -m '{"name": "garden", "device_class": "motion", \
                "state_topic": "homeassistant/binary_sensor/garden/state"}'
        """
        config_message = json.dumps(self.generate_config())

        logger.debug(
            f"Writing '{config_message}' to topic {self.config_topic} on {self._settings.mqtt.host}:{self._settings.mqtt.port}"
        )
        self.wrote_configuration = True
        self.config_message = config_message

        if self._settings.debug:
            logger.debug("Debug mode is enabled, skipping config write.")
            return None

        return self.mqtt_client.publish(self.config_topic, config_message, retain=True)

    def set_attributes(self, attributes: dict[str, object]) -> None:
        """Update the attributes of the entity

        Args:
            attributes: dictionary containing all the attributes that will be \
            set for this entity
        """
        # HA expects a JSON object in the attribute topic
        json_attributes = json.dumps(attributes)
        logger.debug("Updating attributes: %s", json_attributes)
        self._state_helper(json_attributes, topic=self.attributes_topic)

    def set_availability(self, availability: bool):
        if not hasattr(self, "availability_topic"):
            raise RuntimeError("Manual availability is not configured for this entity!")
        message = "online" if availability else "offline"
        self._state_helper(message, topic=self.availability_topic)

    def _update_state(self, state: str | float | int | None) -> None:
        """
        Update MQTT device state

        Override in subclasses
        """
        self._state_helper(state=state)

    def __del__(self):
        """Cleanly shutdown the internal MQTT client"""
        logger.debug("Shutting down MQTT client")
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()


class Subscriber(Discoverable[EntityType]):
    """
    Specialized sub-lass that listens to commands coming from an MQTT topic
    """

    _has_command_callback: bool
    _command_topic: str

    def __init__(
        self,
        settings: Settings[EntityType],
        command_callback: MessageCallback[UserDataT] | None = None,
        user_data: UserDataT | None = None,
    ) -> None:
        """
        Entity that listens to commands from an MQTT topic.

        Args:
            settings: Settings for the entity we want to create in Home Assistant.
            See the `Settings` class for the available options.
            command_callback: Optional callback function invoked when there is a command
            coming from the MQTT command topic. If None, no command topic will be published.
        """
        self._has_command_callback = command_callback is not None

        if command_callback is None:
            # No command callback provided - behave like Discoverable
            super().__init__(settings)
            return

        # Callback invoked when the MQTT connection is established
        def on_client_connected(
            client: mqtt.Client,
            _user_data: object,
            _flags: mqtt.ConnectFlags,
            _reason_code: ReasonCode,
            _properties: Properties | None,
        ) -> None:
            result, _ = client.subscribe(self._command_topic, qos=1)
            if result is not mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError("Error subscribing to MQTT command topic")

        # Invoke the parent init
        super().__init__(settings, on_client_connected)
        # Define the command topic to receive commands from HA, using `hmd` topic prefix
        self._command_topic = (
            f"{self._settings.mqtt.state_prefix}/{self._entity_topic}/command"
        )

        # Register the user-supplied callback function with its user_data
        self.mqtt_client.user_data_set(user_data)
        self.mqtt_client.on_message = cast(mqtt.CallbackOnMessage, command_callback)

        # Manually connect the MQTT client
        self._connect_client()

    @override
    def generate_config(self) -> dict[str, object]:
        """Override base config to add the command topic if callback was provided"""
        config = super().generate_config()

        # Only add command topic if callback was provided
        if self._has_command_callback:
            topics = {
                "command_topic": self._command_topic,
            }
            return config | topics
        else:
            return config
