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
from typing import Annotated, NotRequired, override

from pydantic import Field, HttpUrl, TypeAdapter, ValidationError
from typing_extensions import TypedDict

from ha_mqtt_discoverable._base import Subscriber
from ha_mqtt_discoverable._logging import get_logger
from ha_mqtt_discoverable._models import EntityInfo
from ha_mqtt_discoverable._session import CommandCallback, SessionLike
from ha_mqtt_discoverable._topic_paths import build_state_topic

logger = get_logger(__name__)


class UpdateInfo(EntityInfo):
    """Update specific information"""

    component: str = "update"
    device_class: str | None = None
    """Sets the class of the device, changing the device state and icon that is
    displayed on the frontend. For Update entities, use "firmware" for firmware updates
    or None (default) for generic software updates."""
    display_precision: int = 0
    """The number of decimal places for version display precision."""
    entity_picture: str | None = None
    """Picture URL for the entity."""
    latest_version_template: str | None = None
    """Defines a template to extract the latest version value."""
    latest_version_topic: str | None = None
    """The MQTT topic subscribed to receive the latest version."""
    payload_install: str = "INSTALL"
    """The payload to send to trigger the update installation."""
    release_summary: str | None = None
    """Summary of the release."""
    release_url: str | None = None
    """URL to the release page."""
    title: str | None = None
    """Title of the update."""
    value_template: str | None = None
    """Defines a template to extract the installed version value."""


class UpdateStatePayload(TypedDict, total=False):
    """TypedDict for Update entity JSON state payloads.

    Matches Home Assistant's MQTT_JSON_UPDATE_SCHEMA for full compatibility.
    Note: Only JSON payloads are supported - non-JSON payloads are not supported by this implementation.
    """

    installed_version: NotRequired[str]
    latest_version: NotRequired[str]
    title: NotRequired[str]
    release_summary: NotRequired[str]
    release_url: NotRequired[HttpUrl]
    entity_picture: NotRequired[HttpUrl]
    in_progress: NotRequired[bool]
    update_percentage: NotRequired[Annotated[int, Field(ge=0, le=100)]]


update_state_validator = TypeAdapter(UpdateStatePayload)


class Update(Subscriber[UpdateInfo]):
    """
    Implements an MQTT update for Home Assistant MQTT discovery:
    https://www.home-assistant.io/integrations/update.mqtt/

    This class provides support for Home Assistant Update entities, allowing you to:
    1. Post update availability information with full metadata support
    2. Automatically register with Home Assistant via MQTT discovery
    3. Receive install command callbacks from Home Assistant
    4. Track installation progress with percentage updates
    5. Dynamically update metadata (title, release info, entity picture)

    Features:
    - JSON payload validation using Pydantic models
    - Full compatibility with Home Assistant's MQTT Update schema
    - Automatic in_progress=True when update_percentage is set
    - Support for all HA Update entity configuration options

    Example:
        Basic usage with device context and rich metadata:

        >>> from ha_mqtt_discoverable import DeviceInfo, MqttSession, Settings
        >>> from ha_mqtt_discoverable.sensors import Update, UpdateInfo
        >>>
        >>> # Define device info
        >>> device = DeviceInfo(
        ...     name="My Device",
        ...     identifiers="device_123",
        ...     manufacturer="Example Corp",
        ...     model="Model X"
        ... )
        >>>
        >>> # Create update entity info with full configuration
        >>> update_info = UpdateInfo(
        ...     name="firmware_update",
        ...     device=device,
        ...     unique_id="device_123_firmware",
        ...     title="Device Firmware",
        ...     device_class="firmware",
        ...     display_precision=0,
        ...     entity_picture="https://example.com/device.png"
        ... )
        >>>
        >>> # Define install callback
        >>> async def handle_install(sender, message):
        ...     print("Install command received!")
        ...     # Start your update process here
        ...     await sender.set_progress(0)
        ...     # ... perform update steps ...
        ...     await sender.set_progress(50)
        ...     await sender.set_progress(100)
        >>>
        >>> async with MqttSession(Settings.MQTT(host="localhost")) as mqtt:
        ...     update = Update(mqtt, update_info, handle_install)
        ...     await update.set_state(
        ...     installed="1.2.3",
        ...     latest="1.2.4",
        ...     title="Major Security Update",
        ...     release_summary="Critical security fixes and performance improvements",
        ...     release_url="https://example.com/releases/1.2.4",
        ...     entity_picture="https://example.com/update-icon.png"
        ...     )
        ...     await update.set_state(installed="1.2.3", latest="1.2.4", progress=25)
        ...     await update.set_progress(75)  # Automatically sets in_progress=True
    """

    _latest_version_topic: str

    def __init__(
        self,
        session: SessionLike,
        entity: UpdateInfo,
        command_callback: CommandCallback[Update] | None = None,
    ) -> None:
        """
        Initialize the Update entity.

        Args:
            session: Active MQTT session for the entity
            entity: Entity configuration
            command_callback: Optional async callback invoked when install command is received.
                If None, no command topic will be published and the entity will be read-only.
        """
        super().__init__(session, entity, command_callback)

        self._latest_version_topic = (
            self._entity.latest_version_topic
            or build_state_topic(
                session.state_prefix, self._entity_topic, "latest_version"
            )
        )

    async def set_installed_version(self, version: str) -> None:
        """
        Update the installed version.

        Args:
            version: The currently installed version
        """
        logger.info(
            "setting installed version",
            entity=self._entity.name,
            version=version,
        )
        state: UpdateStatePayload = {"installed_version": version, "in_progress": False}
        await self._update_state(state)

    async def set_latest_version(self, version: str) -> None:
        """
        Update the latest available version.

        Args:
            version: The latest available version
        """
        logger.info(
            "setting latest version",
            entity=self._entity.name,
            version=version,
        )
        await self._state_helper(version, topic=self._latest_version_topic)

    async def set_progress(self, progress: int) -> None:
        """
        Update the installation progress.

        Args:
            progress: Progress percentage (0-100)
        """
        if not 0 <= progress <= 100:
            raise ValueError(f"Progress must be between 0 and 100, got {progress}")

        state: UpdateStatePayload = {"in_progress": True, "update_percentage": progress}
        logger.info(
            "setting update progress",
            entity=self._entity.name,
            progress=progress,
        )
        await self._update_state(state)

    async def set_state(
        self,
        *,
        installed: str,
        latest: str | None = None,
        in_progress: bool = False,
        progress: int | None = None,
        title: str | None = None,
        release_summary: str | None = None,
        release_url: str | None = None,
        entity_picture: str | None = None,
    ) -> None:
        """
        Update the complete update state.

        All arguments are keyword-only to prevent confusion.

        Args:
            installed: Currently installed version
            latest: Latest available version (optional)
            in_progress: Whether an update is currently in progress
            progress: Update progress percentage (0-100, optional). When set, automatically sets in_progress=True
            title: Title of the update (optional)
            release_summary: Summary of the release (optional)
            release_url: URL to the release page (optional)
            entity_picture: Picture URL for the entity (optional)

        Example:
            await update.set_state(installed="1.0.0", latest="1.1.0")
            await update.set_state(installed="1.0.0", latest="1.1.0", in_progress=True, progress=50)
            await update.set_state(installed="1.0.0", latest="1.1.0", title="Major Update", release_summary="Bug fixes")
        """
        state: dict[str, object] = {"installed_version": installed}

        if latest is not None:
            state["latest_version"] = latest
        if title is not None:
            state["title"] = title
        if release_summary is not None:
            state["release_summary"] = release_summary
        if release_url is not None:
            state["release_url"] = release_url
        if entity_picture is not None:
            state["entity_picture"] = entity_picture

        if progress is not None:
            if not 0 <= progress <= 100:
                raise ValueError(f"Progress must be between 0 and 100, got {progress}")
            state["update_percentage"] = progress
            in_progress = True

        state["in_progress"] = in_progress

        logger.info(
            "setting complete update state", entity=self._entity.name, state=state
        )
        await self._update_state(state)

    @override
    async def _update_state(
        self, state: str | float | int | None | Mapping[str, object]
    ) -> None:
        """
        Update MQTT entity state with JSON validation.

        Args:
            state: State payload to publish as JSON

        Note: Only JSON payloads are supported - non-JSON payloads are not supported by this implementation.
        """
        if not isinstance(state, Mapping):
            raise TypeError("Update state payload must be a mapping")

        filtered_state = {k: v for k, v in state.items() if v is not None}

        try:
            validated_payload = update_state_validator.validate_python(filtered_state)
            json_state = update_state_validator.dump_json(validated_payload).decode(
                "utf-8"
            )
            logger.debug(
                "validated update state payload",
                entity=self._entity.name,
                payload=validated_payload,
            )
            await self._state_helper(json_state)
        except ValidationError as e:
            logger.error(
                "invalid update state payload",
                entity=self._entity.name,
                error=str(e),
            )
            raise ValueError(f"Invalid update state payload: {e}") from e

    @override
    def generate_config(self) -> dict[str, object]:
        """Override base config to add update-specific topics and configuration options"""
        config = super().generate_config()

        update_config: dict[str, object] = {}

        if self._entity.display_precision != 0:
            update_config["display_precision"] = self._entity.display_precision
        if self._entity.device_class is not None:
            update_config["device_class"] = self._entity.device_class
        if self._entity.entity_picture is not None:
            update_config["entity_picture"] = self._entity.entity_picture
        if self._entity.latest_version_template is not None:
            update_config["latest_version_template"] = (
                self._entity.latest_version_template
            )
        if hasattr(self, "_latest_version_topic"):
            update_config["latest_version_topic"] = self._latest_version_topic
        if self._entity.release_summary is not None:
            update_config["release_summary"] = self._entity.release_summary
        if self._entity.release_url is not None:
            update_config["release_url"] = self._entity.release_url
        if self._entity.title is not None:
            update_config["title"] = self._entity.title
        if self._entity.value_template is not None:
            update_config["value_template"] = self._entity.value_template

        update_config["payload_install"] = self._entity.payload_install

        return config | update_config
