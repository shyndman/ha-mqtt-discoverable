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
from typing import override

from pydantic import model_validator

from ha_mqtt_discoverable._base import Discoverable, Subscriber
from ha_mqtt_discoverable._models import DeviceInfo, EntityInfo

logger = logging.getLogger(__name__)


class DeviceTriggerInfo(EntityInfo):
    """Information about the device trigger"""

    component: str = "device_automation"
    automation_type: str = "trigger"
    """The type of automation, must be ‘trigger’."""

    payload: str | None = None
    """Optional payload to match the payload being sent over the topic."""
    type: str
    """The type of the trigger"""
    subtype: str
    """The subtype of the trigger"""
    device: DeviceInfo | None = None
    """Information about the device this sensor belongs to (required)"""

    @model_validator(mode="after")
    def require_device(self) -> DeviceTriggerInfo:
        if self.device is None:
            raise ValueError("A device is required for device triggers")
        return self


class DeviceTrigger(Discoverable[DeviceTriggerInfo]):
    """Implements an MQTT Device Trigger
    https://www.home-assistant.io/integrations/device_trigger.mqtt/
    """

    @override
    def generate_config(self) -> dict[str, object]:
        """Publish a custom configuration: since this entity does not provide a
        `state_topic`, HA expects a `topic` key in the config
        """
        config = super().generate_config()
        # Publish our `state_topic` as `topic`
        topics = {
            "topic": self.state_topic,
        }
        return config | topics

    def trigger(self, payload: str | None = None):
        """
        Generate a device trigger event

        Args:
            payload: custom payload to send in the trigger topic

        """
        return self._state_helper(payload, self.state_topic, retain=False)


class CameraInfo(EntityInfo):
    """
    Information about the 'camera' entity.
    """

    component: str = "camera"
    """The component type is 'camera' for this entity."""
    availability_topic: str | None = None
    """The MQTT topic subscribed to publish the camera availability."""
    payload_available: str | None = "online"
    """Payload to publish to indicate the camera is online."""
    payload_not_available: str | None = "offline"
    """Payload to publish to indicate the camera is offline."""
    topic: str | None = None
    """
    The MQTT topic to subscribe to receive an image URL. A url_template option can extract the URL from the message.
    The content_type will be derived from the image when downloaded.
    """
    retain: bool | None = None
    """If the published message should have the retain flag on or not."""


class Camera(Subscriber[CameraInfo]):
    """
    Implements an MQTT camera for Home Assistant MQTT discovery:
    https://www.home-assistant.io/integrations/image.mqtt/
    """

    def set_topic(self, image_topic: str) -> None:
        """
        Update the camera state (image URL).

        Args:
            image_topic (str): Topic of the image to be set as the camera state.
        """
        if not image_topic:
            raise RuntimeError("Image topic cannot be empty")

        logger.info(
            f"Publishing camera image topic {image_topic} to {self._entity.topic}"
        )
        self._state_helper(image_topic)

    @override
    def set_availability(self, availability: bool) -> None:
        """
        Update the camera availability status.

        Args:
            availability (bool): Whether the camera is available or not.
        """
        availability_topic = self._entity.availability_topic
        if availability_topic is None:
            raise RuntimeError("Camera availability topic is not configured")

        payload = (
            self._entity.payload_available or "online"
            if availability
            else self._entity.payload_not_available or "offline"
        )
        retain = True if self._entity.retain is None else self._entity.retain
        logger.info(
            f"Setting camera availability to {payload} using {availability_topic}"
        )
        self.mqtt_client.publish(availability_topic, payload, retain=retain)


class ImageInfo(EntityInfo):
    """
    Information about the 'image' entity.
    """

    component: str = "image"
    """The component type is 'image' for this entity."""
    availability_topic: str | None = None
    """The MQTT topic subscribed to publish the image availability."""
    payload_available: str | None = "online"
    """Payload to publish to indicate the image is online."""
    payload_not_available: str | None = "offline"
    """Payload to publish to indicate the image is offline."""
    url_topic: str | None = None
    """
    The MQTT topic to subscribe to receive an image URL. A url_template option can extract the URL from the message.
    The content_type will be derived from the image when downloaded.
    """
    retain: bool | None = None
    """If the published message should have the retain flag on or not."""


class Image(Discoverable[ImageInfo]):
    """
    Implements an MQTT image for Home Assistant MQTT discovery:
    https://www.home-assistant.io/integrations/image.mqtt/
    """

    def set_url(self, image_url: str) -> None:
        """
        Update the camera state (image URL).

        Args:
            image_url (str): URL of the image to be set as the camera state.
        """
        if not image_url:
            raise RuntimeError("Image URL cannot be empty")

        logger.info(f"Publishing image URL {image_url} to {self._entity.url_topic}")
        self._state_helper(image_url, self._entity.url_topic)
