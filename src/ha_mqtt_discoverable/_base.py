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
from typing import Generic, Protocol, cast, override

import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessageInfo
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from ha_mqtt_discoverable._models import EntityType, Settings, UserDataT
from ha_mqtt_discoverable._topic_paths import (
    build_command_topic,
    build_config_topic,
    build_entity_topic,
    build_state_topic,
)

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


logger = logging.getLogger(__name__)


class Discoverable(Generic[EntityType]):
    """
    Base class for making MQTT discoverable objects
    """

    _settings: Settings[EntityType]
    _entity: EntityType

    mqtt_client: mqtt.Client
    _owns_mqtt_client: bool
    _started_mqtt_connection: bool
    _started_mqtt_loop: bool
    _closed: bool
    wrote_configuration: bool = False
    debug: bool = False
    config_message: str = ""
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
        super().__init__()
        self._settings = settings
        self._entity = settings.entity
        self._owns_mqtt_client = settings.mqtt.client is None
        self._started_mqtt_connection = False
        self._started_mqtt_loop = False
        self._closed = False

        self._entity_topic = build_entity_topic(self._entity)
        self.config_topic = build_config_topic(
            self._settings.mqtt.discovery_prefix,
            self._entity_topic,
        )
        self.state_topic = build_state_topic(
            self._settings.mqtt.state_prefix,
            self._entity_topic,
        )
        self.attributes_topic = build_state_topic(
            self._settings.mqtt.state_prefix,
            self._entity_topic,
            "attributes",
        )

        logger.info(f"config_topic: {self.config_topic}")
        logger.info(f"state_topic: {self.state_topic}")
        if self._settings.manual_availability:
            self.availability_topic = build_state_topic(
                self._settings.mqtt.state_prefix,
                self._entity_topic,
                "availability",
            )
            logger.debug(f"availability_topic: {self.availability_topic}")

        self._setup_client(on_connect)
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
                    mqtt_settings.username,
                    password=mqtt_settings.password,
                )
        else:
            logger.debug(
                f"Connecting to {mqtt_settings.host}:{mqtt_settings.port} without SSL"
            )
            if mqtt_settings.username:
                self.mqtt_client.username_pw_set(
                    mqtt_settings.username,
                    password=mqtt_settings.password,
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
        if result != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                f"Failed to connect to MQTT broker at {host}:{port}, error code: {result}"
            )
            raise RuntimeError("Error while connecting to MQTT broker")

        logger.debug(f"Successfully connected to MQTT broker at {host}:{port}")
        self._started_mqtt_connection = True

        logger.debug("Starting MQTT client loop in separate thread")
        self.mqtt_client.loop_start()
        self._started_mqtt_loop = True
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
            return None

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
        config = cast(
            dict[str, object],
            self._entity.model_dump(exclude_none=True, exclude={"object_id"}),
        )

        if self._entity.object_id:
            config["default_entity_id"] = (
                f"{self._entity.component}.{self._entity.object_id}"
            )

        topics = {
            "state_topic": self.state_topic,
            "json_attributes_topic": self.attributes_topic,
        }
        if hasattr(self, "availability_topic"):
            topics["availability_topic"] = self.availability_topic
        return config | topics

    def write_config(self) -> MQTTMessageInfo | None:
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
        json_attributes = json.dumps(attributes)
        logger.debug("Updating attributes: %s", json_attributes)
        self._state_helper(json_attributes, topic=self.attributes_topic)

    def set_availability(self, availability: bool) -> None:
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

    def close(self) -> None:
        """Cleanly shutdown an internally managed MQTT client."""
        if self._closed:
            return

        self._closed = True

        if not self._owns_mqtt_client:
            return

        logger.debug("Shutting down MQTT client")
        if self._started_mqtt_connection:
            self.mqtt_client.disconnect()
            self._started_mqtt_connection = False
        if self._started_mqtt_loop:
            self.mqtt_client.loop_stop()
            self._started_mqtt_loop = False


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
        self._command_topic = build_command_topic(
            settings.mqtt.state_prefix,
            build_entity_topic(settings.entity),
        )

        if command_callback is None:
            super().__init__(settings)
            return

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

        super().__init__(settings, on_client_connected)
        self.mqtt_client.user_data_set(user_data)
        self.mqtt_client.on_message = cast(mqtt.CallbackOnMessage, command_callback)
        self._connect_client()

    @override
    def generate_config(self) -> dict[str, object]:
        """Override base config to add the command topic if callback was provided"""
        config = super().generate_config()

        if self._has_command_callback:
            topics = {
                "command_topic": self._command_topic,
            }
            return config | topics
        return config
