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
from typing import Generic, Self, cast, override

from ha_mqtt_discoverable._logging import get_logger
from ha_mqtt_discoverable._models import EntityType
from ha_mqtt_discoverable._session import CommandCallback, PublishPayload, SessionLike
from ha_mqtt_discoverable._topic_paths import (
    build_command_topic,
    build_config_topic,
    build_entity_topic,
    build_state_topic,
)

logger = get_logger(__name__)


class Discoverable(Generic[EntityType]):
    """
    Base class for making MQTT discoverable objects
    """

    _session: SessionLike
    _entity: EntityType
    wrote_configuration: bool = False
    _entity_topic: str
    config_topic: str
    state_topic: str
    availability_topic: str
    attributes_topic: str
    _requires_connection: bool
    _available: bool

    def __init__(
        self,
        session: SessionLike,
        entity: EntityType,
        *,
        requires_connection: bool = True,
    ) -> None:
        super().__init__()
        self._session = session
        self._entity = entity
        self._requires_connection = requires_connection
        self._available = True

        self._entity_topic = build_entity_topic(self._entity)
        self.config_topic = build_config_topic(
            self._session.discovery_prefix,
            self._entity_topic,
        )
        self.state_topic = build_state_topic(
            self._session.state_prefix,
            self._entity_topic,
        )
        self.attributes_topic = build_state_topic(
            self._session.state_prefix,
            self._entity_topic,
            "attributes",
        )

        logger.info(
            "initialized mqtt entity topics",
            entity=self._entity.name,
            component=self._entity.component,
            config_topic=self.config_topic,
            state_topic=self.state_topic,
        )
        self.availability_topic = build_state_topic(
            self._session.state_prefix,
            self._entity_topic,
            "availability",
        )

    @override
    def __str__(self) -> str:
        """
        Generate a string representation of the Discoverable object
        """
        return (
            f"settings: {self._entity}\n"
            f"topic_prefix: {self._entity_topic}\n"
            f"config_topic: {self.config_topic}\n"
            f"state_topic: {self.state_topic}\n"
            f"wrote_configuration: {self.wrote_configuration}\n"
        )

    @property
    def entity(self) -> EntityType:
        return self._entity

    async def _publish(
        self,
        topic: str,
        payload: PublishPayload,
        *,
        retain: bool,
    ) -> None:
        await self._session.publish(topic, payload, retain=retain)

    async def _state_helper(
        self,
        state: str | float | int | None,
        topic: str | None = None,
        last_reset: str | None = None,
        retain: bool = True,
    ) -> None:
        """
        Write a state to the given MQTT topic.
        """
        if not self.wrote_configuration:
            await self.write_config()
        if topic is None:
            topic = self.state_topic
        payload: PublishPayload = state
        if last_reset:
            payload = json.dumps({"state": state, "last_reset": last_reset})
        logger.debug(
            "publishing entity state",
            entity=self._entity.name,
            component=self._entity.component,
            topic=topic,
            retain=retain,
        )
        await self._publish(topic, payload, retain=retain)

    async def delete(self) -> None:
        """
        Delete a synthetic sensor from Home Assistant via MQTT message.

        Based on https://www.home-assistant.io/docs/mqtt/discovery/
        """
        logger.info(
            "deleting mqtt discovery config",
            entity=self._entity.name,
            component=self._entity.component,
            topic=self.config_topic,
        )
        await self._publish(self.config_topic, "", retain=True)

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

        topics: dict[str, object] = {
            "state_topic": self.state_topic,
            "json_attributes_topic": self.attributes_topic,
        }
        if self._requires_connection:
            # Available only while the publisher's connection is alive (session
            # status topic + LWT) AND the manual availability says so.
            topics["availability"] = [
                {"topic": self._session.status_topic},
                {"topic": self.availability_topic},
            ]
            topics["availability_mode"] = "all"
        else:
            topics["availability_topic"] = self.availability_topic
        return config | topics

    async def write_config(self) -> None:
        config_message = json.dumps(self.generate_config())

        logger.debug(
            "writing mqtt discovery config",
            entity=self._entity.name,
            component=self._entity.component,
            topic=self.config_topic,
        )
        await self._publish(self.config_topic, config_message, retain=True)
        self.wrote_configuration = True
        # Publish the current manual availability once at registration so HA learns
        # the entity's availability immediately (config first, then availability).
        await self._publish(
            self.availability_topic,
            "online" if self._available else "offline",
            retain=True,
        )

    async def set_attributes(self, attributes: dict[str, object]) -> None:
        """Update the attributes of the entity

        Args:
            attributes: dictionary containing all the attributes that will be \
            set for this entity
        """
        await self._state_helper(
            json.dumps(attributes),
            topic=self.attributes_topic,
        )

    @property
    def available(self) -> bool:
        """Whether the represented thing is currently usable (manual availability)."""
        return self._available

    async def set_available(self, available: bool) -> None:
        self._available = available
        if not self.wrote_configuration:
            # write_config publishes the initial availability from self._available,
            # so the first set_available is satisfied by writing config.
            await self.write_config()
            return
        await self._publish(
            self.availability_topic,
            "online" if available else "offline",
            retain=True,
        )

    async def _update_state(self, state: str | float | int | None) -> None:
        """
        Update MQTT device state

        Override in subclasses
        """
        await self._state_helper(state=state)


class Subscriber(Discoverable[EntityType]):
    """
    Specialized sub-class that listens to commands coming from an MQTT topic
    """

    _has_command_callback: bool
    _command_topic: str

    def __init__(
        self,
        session: SessionLike,
        entity: EntityType,
        command_callback: CommandCallback[Self] | None = None,
        *,
        requires_connection: bool = True,
    ) -> None:
        self._has_command_callback = command_callback is not None
        self._command_topic = build_command_topic(
            session.state_prefix,
            build_entity_topic(entity),
        )
        super().__init__(
            session,
            entity,
            requires_connection=requires_connection,
        )

        if command_callback is not None:
            session.register_command(
                self._command_topic,
                self,
                command_callback,
                command_name="command",
            )

    @override
    def generate_config(self) -> dict[str, object]:
        """Override base config to add the command topic if callback was provided"""
        config = super().generate_config()
        if self._has_command_callback:
            return config | {"command_topic": self._command_topic}
        return config
