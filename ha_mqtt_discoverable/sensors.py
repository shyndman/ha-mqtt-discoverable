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
# Required to define a class itself as type https://stackoverflow.com/a/33533514
from __future__ import annotations

import json
import logging
from typing import Annotated, Any, Optional

from pydantic import Field

from ha_mqtt_discoverable import (
    DeviceInfo,
    Discoverable,
    EntityInfo,
    Subscriber,
)

logger = logging.getLogger(__name__)


class BinarySensorInfo(EntityInfo):
    """Binary sensor specific information"""

    component: str = "binary_sensor"
    off_delay: Optional[int] = None
    """For sensors that only send on state updates (like PIRs), this variable
    sets a delay in seconds after which the sensor's state will be updated back
    to off."""
    payload_off: str = "off"
    """Payload to send for the ON state"""
    payload_on: str = "on"
    """Payload to send for the OFF state"""


class SensorInfo(EntityInfo):
    """Sensor specific information"""

    component: str = "sensor"
    unit_of_measurement: Optional[str] = None
    """Defines the units of measurement of the sensor, if any."""
    state_class: Optional[str] = None
    """Defines the type of state.
    If not None, the sensor is assumed to be numerical
    and will be displayed as a line-chart
    in the frontend instead of as discrete values."""
    value_template: Optional[str] = None
    """
    Defines a template to extract the value.
    If the template throws an error,
    the current state will be used instead."""
    last_reset_value_template: Optional[str] = None
    """
    Defines a template to extract the last_reset.
    When last_reset_value_template is set, the state_class option must be total.
    Available variables: entity_id.
    The entity_id can be used to reference the entity’s attributes."""
    suggested_display_precision: None | Annotated[int, Field(ge=0)] = None
    """
    The number of decimals which should be used in the sensor’s state after rounding.
    """


class SwitchInfo(EntityInfo):
    """Switch specific information"""

    component: str = "switch"
    optimistic: Optional[bool] = None
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
    retain: Optional[bool] = None
    """If the published message should have the retain flag on or not"""
    state_topic: Optional[str] = None
    """The MQTT topic subscribed to receive state updates."""


class LightInfo(EntityInfo):
    """Light specific information"""

    component: str = "light"

    state_schema: str = Field(default="json", alias="schema")  # 'schema' is a reserved word by pydantic
    """Sets the schema of the state topic, ie the 'schema' field in the configuration"""
    optimistic: Optional[bool] = None
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
    brightness: Optional[bool] = False
    """Flag that defines if the light supports setting the brightness
    """
    color_mode: Optional[bool] = None
    """Flag that defines if the light supports color mode"""
    supported_color_modes: Optional[list[str]] = None
    """List of supported color modes. See
    https://www.home-assistant.io/integrations/light.mqtt/#supported_color_modes for current list of
    supported modes. Required if color_mode is set"""
    effect: Optional[bool] = False
    """Flag that defines if the light supports effects"""
    effect_list: Optional[str | list] = None
    """List of supported effects. Required if effect is set"""
    retain: Optional[bool] = True
    """If the published message should have the retain flag on or not"""
    state_topic: Optional[str] = None
    """The MQTT topic subscribed to receive state updates."""


class CoverInfo(EntityInfo):
    """Cover specific information"""

    component: str = "cover"

    optimistic: Optional[bool] = None
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
    state_topic: Optional[str] = None
    """The MQTT topic subscribed to receive state updates."""
    retain: Optional[bool] = True
    """If the published message should have the retain flag on or not"""


class ButtonInfo(EntityInfo):
    """Button specific information"""

    component: str = "button"

    payload_press: str = "PRESS"
    """The payload to send to trigger the button."""
    retain: Optional[bool] = None
    """If the published message should have the retain flag on or not"""


class TextInfo(EntityInfo):
    """Information about the `text` entity"""

    component: str = "text"

    max: int = 255
    """The maximum size of a text being set or received (maximum is 255)."""
    min: int = 0
    """The minimum size of a text being set or received."""
    mode: Optional[str] = "text"
    """The mode off the text entity. Must be either text or password."""
    pattern: Optional[str] = None
    """A valid regular expression the text being set or received must match with."""

    retain: Optional[bool] = None
    """If the published message should have the retain flag on or not"""


class NumberInfo(EntityInfo):
    """Information about the 'number' entity"""

    component: str = "number"

    max: float | int = 100
    """The maximum value of the number (defaults to 100)"""
    min: float | int = 1
    """The maximum value of the number (defaults to 1)"""
    mode: Optional[str] = None
    """Control how the number should be displayed in the UI. Can be set to box
    or slider to force a display mode."""
    optimistic: Optional[bool] = None
    """Flag that defines if switch works in optimistic mode.
    Default: true if no state_topic defined, else false."""
    payload_reset: Optional[str] = None
    """A special payload that resets the state to None when received on the
    state_topic."""
    retain: Optional[bool] = None
    """If the published message should have the retain flag on or not"""
    state_topic: Optional[str] = None
    """The MQTT topic subscribed to receive state updates."""
    step: Optional[float] = None
    """Step value. Smallest acceptable value is 0.001. Defaults to 1.0."""
    unit_of_measurement: Optional[str] = None
    """Defines the unit of measurement of the sensor, if any. The
    unit_of_measurement can be null."""


class DeviceTriggerInfo(EntityInfo):
    """Information about the device trigger"""

    component: str = "device_automation"
    automation_type: str = "trigger"
    """The type of automation, must be ‘trigger’."""

    payload: Optional[str] = None
    """Optional payload to match the payload being sent over the topic."""
    type: str
    """The type of the trigger"""
    subtype: str
    """The subtype of the trigger"""
    device: DeviceInfo
    """Information about the device this sensor belongs to (required)"""


class CameraInfo(EntityInfo):
    """
    Information about the 'camera' entity.
    """

    component: str = "camera"
    """The component type is 'camera' for this entity."""
    availability_topic: Optional[str] = None
    """The MQTT topic subscribed to publish the camera availability."""
    payload_available: Optional[str] = "online"
    """Payload to publish to indicate the camera is online."""
    payload_not_available: Optional[str] = "offline"
    """Payload to publish to indicate the camera is offline."""
    topic: Optional[str] = None
    """
    The MQTT topic to subscribe to receive an image URL. A url_template option can extract the URL from the message.
    The content_type will be derived from the image when downloaded.
    """
    retain: Optional[bool] = None
    """If the published message should have the retain flag on or not."""


class ImageInfo(EntityInfo):
    """
    Information about the 'image' entity.
    """

    component: str = "image"
    """The component type is 'image' for this entity."""
    availability_topic: Optional[str] = None
    """The MQTT topic subscribed to publish the image availability."""
    payload_available: Optional[str] = "online"
    """Payload to publish to indicate the image is online."""
    payload_not_available: Optional[str] = "offline"
    """Payload to publish to indicate the image is offline."""
    url_topic: Optional[str] = None
    """
    The MQTT topic to subscribe to receive an image URL. A url_template option can extract the URL from the message.
    The content_type will be derived from the image when downloaded.
    """
    retain: Optional[bool] = None
    """If the published message should have the retain flag on or not."""


class SelectInfo(EntityInfo):
    """Switch specific information"""

    component: str = "select"
    optimistic: Optional[bool] = None
    """Flag that defines if switch works in optimistic mode.
    Default: true if no state_topic defined, else false."""
    retain: Optional[bool] = None
    """If the published message should have the retain flag on or not"""
    state_topic: Optional[str] = None
    """The MQTT topic subscribed to receive state updates."""
    options: Optional[list] = None
    """List of options that can be selected. An empty list or a list with a single item is allowed."""


class UpdateInfo(EntityInfo):
    """Update specific information"""

    component: str = "update"
    device_class: Optional[str] = None
    """Sets the class of the device, changing the device state and icon that is
    displayed on the frontend. For Update entities, use "firmware" for firmware updates
    or None (default) for generic software updates."""
    entity_picture: Optional[str] = None
    """Picture URL for the entity."""
    latest_version_template: Optional[str] = None
    """Defines a template to extract the latest version value."""
    latest_version_topic: Optional[str] = None
    """The MQTT topic subscribed to receive the latest version."""
    payload_install: str = "INSTALL"
    """The payload to send to trigger the update installation."""
    release_summary: Optional[str] = None
    """Summary of the release."""
    release_url: Optional[str] = None
    """URL to the release page."""
    title: Optional[str] = None
    """Title of the update."""
    value_template: Optional[str] = None
    """Defines a template to extract the installed version value."""


<<<<<<< HEAD
||||||| parent of 04ae7e8 (Trailing newline)
class MediaPlayerInfo(EntityInfo):
    """Media Player specific information"""

    component: str = "media_player"

    # Availability configuration
    availability_topic: Optional[str] = None
    """The MQTT topic subscribed to receive availability (online/offline) updates."""
    payload_available: str = "online"
    """The payload that represents the available state."""
    payload_not_available: str = "offline"
    """The payload that represents the unavailable state."""

    # State topics
    state_topic: Optional[str] = None
    """The MQTT topic subscribed to receive state updates (playing, paused, stopped, idle, off)."""
    title_topic: Optional[str] = None
    """The MQTT topic subscribed to receive the current track title."""
    artist_topic: Optional[str] = None
    """The MQTT topic subscribed to receive the current track artist."""
    album_topic: Optional[str] = None
    """The MQTT topic subscribed to receive the current track album."""
    duration_topic: Optional[str] = None
    """The MQTT topic subscribed to receive the current track duration in seconds."""
    position_topic: Optional[str] = None
    """The MQTT topic subscribed to receive the current playback position in seconds."""
    volume_topic: Optional[str] = None
    """The MQTT topic subscribed to receive the current volume level (0.0-1.0)."""
    albumart_topic: Optional[str] = None
    """The MQTT topic subscribed to receive album art (base64 encoded or URL)."""
    mediatype_topic: Optional[str] = None
    """The MQTT topic subscribed to receive media type (music, video, etc.)."""

    # Command topics
    play_topic: Optional[str] = None
    """The MQTT topic to send play commands to."""
    play_payload: str = "Play"
    """The payload to send when requesting play."""
    pause_topic: Optional[str] = None
    """The MQTT topic to send pause commands to."""
    pause_payload: str = "Pause"
    """The payload to send when requesting pause."""
    stop_topic: Optional[str] = None
    """The MQTT topic to send stop commands to."""
    stop_payload: str = "Stop"
    """The payload to send when requesting stop."""
    next_topic: Optional[str] = None
    """The MQTT topic to send next track commands to."""
    next_payload: str = "Next"
    """The payload to send when requesting next track."""
    previous_topic: Optional[str] = None
    """The MQTT topic to send previous track commands to."""
    previous_payload: str = "Previous"
    """The payload to send when requesting previous track."""
    volumeset_topic: Optional[str] = None
    """The MQTT topic to send volume set commands to."""
    playmedia_topic: Optional[str] = None
    """The MQTT topic to send play media commands to (for TTS, URLs, etc.)."""
    seek_topic: Optional[str] = None
    """The MQTT topic to send seek position commands to."""
    browse_media_topic: Optional[str] = None
    """The MQTT topic to send browse media commands to."""


class MediaPlayer(Subscriber[MediaPlayerInfo]):
    """Implements an MQTT media player with flexible capabilities.

    Supports state-only, command-only, and full bidirectional media players.
    Features are dynamically enabled based on configured topics.
    """

    def __init__(self, settings, command_callbacks=None, user_data=None):
        """Initialize the MediaPlayer with optional command callbacks.

        Args:
            settings: Settings for the entity
            command_callbacks: Dict mapping command names to callback functions
            user_data: Optional user data passed to callbacks
        """
        super().__init__(settings, self._command_callback_handler, user_data)
        self._command_callbacks = command_callbacks or {}

    def _command_callback_handler(self, client, user_data, message):
        """Internal handler that routes commands to appropriate callbacks."""
        topic = message.topic
        
        # Decode payload with error handling
        try:
            payload = message.payload.decode()
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode payload for topic {topic}: {e}")
            return

        # Extract command from topic (last part after final slash)
        command_name = topic.split('/')[-1]

        # Map topic names to callback keys
        command_map = {
            'play': 'play',
            'pause': 'pause',
            'stop': 'stop',
            'next': 'next',
            'previous': 'previous',
            'volumeset': 'volume_set',
            'seek': 'seek',
            'playmedia': 'play_media',
            'browse': 'browse_media'
        }

        callback_key = command_map.get(command_name)
        if callback_key and callback_key in self._command_callbacks:
            try:
                # Parse payload for commands that need numeric values
                parsed_payload = self._parse_command_payload(callback_key, payload)
                
                # Call callback with parsed payload
                self._command_callbacks[callback_key](client, user_data, message, parsed_payload)
            except Exception as e:
                logger.error(f"Error in {callback_key} callback: {e}")
        else:
            logger.warning(f"No callback registered for command: {command_name}")

    def _parse_command_payload(self, command_key: str, payload: str):
        """Parse payload for commands that expect specific formats."""
        match command_key:
            case 'volume_set':
                try:
                    volume = float(payload)
                    if 0.0 <= volume <= 1.0:
                        return volume
                    else:
                        logger.warning(f"Volume value {volume} out of range [0.0, 1.0], using raw payload")
                        return payload
                except ValueError:
                    logger.warning(f"Invalid volume payload '{payload}', expected float")
                    return payload
            case 'seek':
                try:
                    position = float(payload)
                    if position >= 0:
                        return position
                    else:
                        logger.warning(f"Seek position {position} is negative, using raw payload")
                        return payload
                except ValueError:
                    logger.warning(f"Invalid seek payload '{payload}', expected float")
                    return payload
            case 'play_media':
                try:
                    import json
                    return json.loads(payload)
                except (json.JSONDecodeError, ImportError):
                    # Not JSON or json module unavailable, return raw payload
                    return payload
            case _:
                # For simple commands (play, pause, stop, etc.), return raw payload
                return payload

    # Core state methods
    def set_state(self, state: str) -> None:
        """Set media player state: playing, paused, stopped, idle, off"""
        if self._entity.state_topic:
            logger.info(f"Setting {self._entity.name} state to {state}")
            self._state_helper(state, topic=self._entity.state_topic)

    def set_availability(self, available: bool) -> None:
        """Set online/offline availability"""
        if self._entity.availability_topic:
            payload = self._entity.payload_available if available else self._entity.payload_not_available
            logger.info(f"Setting {self._entity.name} availability to {payload}")
            self.mqtt_client.publish(self._entity.availability_topic, payload, retain=True)

    # Media metadata methods
    def set_title(self, title: str) -> None:
        """Set current track title"""
        if self._entity.title_topic:
            logger.info(f"Setting {self._entity.name} title to {title}")
            self._state_helper(title, topic=self._entity.title_topic)

    def set_artist(self, artist: str) -> None:
        """Set current track artist"""
        if self._entity.artist_topic:
            logger.info(f"Setting {self._entity.name} artist to {artist}")
            self._state_helper(artist, topic=self._entity.artist_topic)

    def set_album(self, album: str) -> None:
        """Set current album name"""
        if self._entity.album_topic:
            logger.info(f"Setting {self._entity.name} album to {album}")
            self._state_helper(album, topic=self._entity.album_topic)

    def set_media_type(self, media_type: str) -> None:
        """Set media type (music, video, etc.)"""
        if self._entity.mediatype_topic:
            logger.info(f"Setting {self._entity.name} media type to {media_type}")
            self._state_helper(media_type, topic=self._entity.mediatype_topic)

    # Playback information methods
    def set_duration(self, duration: int) -> None:
        """Set track duration in seconds"""
        if self._entity.duration_topic:
            logger.info(f"Setting {self._entity.name} duration to {duration}")
            self._state_helper(str(duration), topic=self._entity.duration_topic)

    def set_position(self, position: int) -> None:
        """Set current playback position in seconds"""
        if self._entity.position_topic:
            logger.info(f"Setting {self._entity.name} position to {position}")
            self._state_helper(str(position), topic=self._entity.position_topic)

    def set_volume(self, volume: float) -> None:
        """Set volume level (0.0-1.0)"""
        if self._entity.volume_topic:
            if not 0.0 <= volume <= 1.0:
                raise ValueError(f"Volume must be between 0.0 and 1.0, got {volume}")
            logger.info(f"Setting {self._entity.name} volume to {volume}")
            self._state_helper(str(volume), topic=self._entity.volume_topic)

    # Album art methods
    def set_albumart_base64(self, image_data: bytes, content_type: str = "image/jpeg") -> None:
        """Set album art from base64 encoded image data"""
        if self._entity.albumart_topic:
            import base64
            b64_data = base64.b64encode(image_data).decode('utf-8')
            logger.info(f"Setting {self._entity.name} album art (base64, {len(image_data)} bytes)")
            self._state_helper(b64_data, topic=self._entity.albumart_topic)

    def set_albumart_url(self, url: str) -> None:
        """Set album art from URL"""
        if self._entity.albumart_topic:
            logger.info(f"Setting {self._entity.name} album art URL to {url}")
            self._state_helper(url, topic=self._entity.albumart_topic)

    # Convenience methods
    def set_media_info(self, title: str = None, artist: str = None,
                      album: str = None, duration: int = None,
                      position: int = None, media_type: str = None) -> None:
        """Set multiple media attributes in one call"""
        if title is not None:
            self.set_title(title)
        if artist is not None:
            self.set_artist(artist)
        if album is not None:
            self.set_album(album)
        if duration is not None:
            self.set_duration(duration)
        if position is not None:
            self.set_position(position)
        if media_type is not None:
            self.set_media_type(media_type)

    def update_playback_status(self, state: str, position: int = None,
                              volume: float = None) -> None:
        """Update playback state, position, and volume together"""
        self.set_state(state)
        if position is not None:
            self.set_position(position)
        if volume is not None:
            self.set_volume(volume)

    # Capability introspection methods
    def can_report_state(self) -> bool:
        """Returns True if any state topics are configured"""
        return any([
            self._entity.state_topic,
            self._entity.title_topic,
            self._entity.artist_topic,
            self._entity.album_topic,
            self._entity.duration_topic,
            self._entity.position_topic,
            self._entity.volume_topic,
            self._entity.albumart_topic,
            self._entity.mediatype_topic
        ])

    def can_accept_commands(self) -> bool:
        """Returns True if any command topics are configured"""
        return any([
            self._entity.play_topic,
            self._entity.pause_topic,
            self._entity.stop_topic,
            self._entity.next_topic,
            self._entity.previous_topic,
            self._entity.volumeset_topic,
            self._entity.playmedia_topic,
            self._entity.seek_topic,
            self._entity.browse_media_topic
        ])

    def can_report_volume(self) -> bool:
        """Returns True if volume_topic is configured"""
        return self._entity.volume_topic is not None

    def can_control_volume(self) -> bool:
        """Returns True if volumeset_topic is configured"""
        return self._entity.volumeset_topic is not None

    def can_report_metadata(self) -> bool:
        """Returns True if title, artist, or album topics are configured"""
        return any([
            self._entity.title_topic,
            self._entity.artist_topic,
            self._entity.album_topic
        ])

    def can_control_playback(self) -> bool:
        """Returns True if play, pause, or stop topics are configured"""
        return any([
            self._entity.play_topic,
            self._entity.pause_topic,
            self._entity.stop_topic
        ])

    def can_seek(self) -> bool:
        """Returns True if seek_topic is configured"""
        return self._entity.seek_topic is not None

    def can_navigate_tracks(self) -> bool:
        """Returns True if next or previous topics are configured"""
        return any([
            self._entity.next_topic,
            self._entity.previous_topic
        ])

    def can_play_media(self) -> bool:
        """Returns True if playmedia_topic is configured"""
        return self._entity.playmedia_topic is not None

    def can_browse_media(self) -> bool:
        """Returns True if browse_media_topic is configured"""
        return self._entity.browse_media_topic is not None

    def get_configured_capabilities(self) -> list[str]:
        """Returns list of capability names that are configured"""
        capabilities = []
        if self.can_report_state():
            capabilities.append("state_reporting")
        if self.can_report_metadata():
            capabilities.append("metadata_reporting")
        if self.can_report_volume():
            capabilities.append("volume_reporting")
        if self.can_control_playback():
            capabilities.append("playback_control")
        if self.can_control_volume():
            capabilities.append("volume_control")
        if self.can_seek():
            capabilities.append("seek_control")
        if self.can_navigate_tracks():
            capabilities.append("track_navigation")
        if self.can_play_media():
            capabilities.append("play_media")
        if self.can_browse_media():
            capabilities.append("browse_media")
        return capabilities

    def get_state_topics(self) -> dict[str, str]:
        """Returns dictionary of configured state topics"""
        topics = {}
        state_topic_attrs = [
            ('state', 'state_topic'),
            ('title', 'title_topic'),
            ('artist', 'artist_topic'),
            ('album', 'album_topic'),
            ('duration', 'duration_topic'),
            ('position', 'position_topic'),
            ('volume', 'volume_topic'),
            ('albumart', 'albumart_topic'),
            ('mediatype', 'mediatype_topic'),
            ('availability', 'availability_topic')
        ]

        for name, attr in state_topic_attrs:
            topic = getattr(self._entity, attr)
            if topic:
                topics[name] = topic
        return topics

    def get_command_topics(self) -> dict[str, str]:
        """Returns dictionary of configured command topics"""
        topics = {}
        command_topic_attrs = [
            ('play', 'play_topic'),
            ('pause', 'pause_topic'),
            ('stop', 'stop_topic'),
            ('next', 'next_topic'),
            ('previous', 'previous_topic'),
            ('volumeset', 'volumeset_topic'),
            ('playmedia', 'playmedia_topic'),
            ('seek', 'seek_topic'),
            ('browse_media', 'browse_media_topic')
        ]

        for name, attr in command_topic_attrs:
            topic = getattr(self._entity, attr)
            if topic:
                topics[name] = topic
        return topics

    def generate_config(self) -> dict[str, Any]:
        """Override to generate discovery config with only configured topics"""
        config = super().generate_config()

        # Remove state_topic if not configured (for command-only players)
        if not self._entity.state_topic:
            config.pop('state_topic', None)

        # Remove payload fields for commands that don't have topics configured
        payload_topic_mappings = [
            ('play_payload', 'play_topic'),
            ('pause_payload', 'pause_topic'),
            ('stop_payload', 'stop_topic'),
            ('next_payload', 'next_topic'),
            ('previous_payload', 'previous_topic')
        ]

        # Remove payloads from config if their corresponding topics aren't configured
        for payload_field, topic_field in payload_topic_mappings:
            if not getattr(self._entity, topic_field):
                config.pop(payload_field, None)

        # Remove availability payloads if availability_topic is not configured
        if not self._entity.availability_topic:
            config.pop('payload_available', None)
            config.pop('payload_not_available', None)
        else:
            # Add availability config block for ha-mqtt-media-player compatibility
            config['availability'] = {
                'payload_available': self._entity.payload_available,
                'payload_not_available': self._entity.payload_not_available,
                'topic': self._entity.availability_topic
            }

        return config


=======
class MediaPlayerInfo(EntityInfo):
    """Enhanced Media Player with property-based state management"""

    component: str = "media_player"

    # === State Properties (represent actual media player state) ===
    
    # Basic state
    state: Optional[str] = None
    """Current state: playing, paused, stopped, idle, off"""
    
    # Media information
    media_title: Optional[str] = None
    """Title of current playing media"""
    
    media_artist: Optional[str] = None
    """Artist of current playing media, music track only"""
    
    media_album_name: Optional[str] = None
    """Album name of current playing media, music track only"""
    
    media_album_artist: Optional[str] = None
    """Album artist of current playing media, music track only"""
    
    media_duration: Optional[int] = None
    """Duration of current playing media in seconds"""
    
    media_position: Optional[int] = None
    """Position of current playing media in seconds"""
    
    media_content_id: Optional[str] = None
    """Content ID of current playing media"""
    
    media_content_type: Optional[str] = None
    """Content type: music, video, podcast, etc."""
    
    media_track: Optional[int] = None
    """Track number of current playing media, music track only"""
    
    media_episode: Optional[str] = None
    """Episode of current playing media, TV show only"""
    
    media_season: Optional[str] = None
    """Season of current playing media, TV show only"""
    
    media_series_title: Optional[str] = None
    """Title of series of current playing media, TV show only"""
    
    media_channel: Optional[str] = None
    """Channel currently playing"""
    
    media_playlist: Optional[str] = None
    """Title of Playlist currently playing"""
    
    # Audio properties
    volume_level: Optional[float] = None
    """Volume level in range 0.0-1.0"""
    
    is_volume_muted: Optional[bool] = None
    """True if volume is currently muted"""
    
    volume_step: Optional[float] = 0.1
    """Volume step for volume_up/volume_down commands"""
    
    # Playback properties
    shuffle: Optional[bool] = None
    """True if shuffle is enabled"""
    
    repeat: Optional[str] = None
    """Current repeat mode: off, all, one"""
    
    # Source/input properties
    source: Optional[str] = None
    """Currently selected input source"""
    
    source_list: Optional[list[str]] = None
    """List of available input sources"""
    
    sound_mode: Optional[str] = None
    """Current sound mode"""
    
    sound_mode_list: Optional[list[str]] = None
    """List of available sound modes"""
    
    # Media image
    media_image_url: Optional[str] = None
    """Image URL of current playing media"""
    
    media_image_remotely_accessible: Optional[bool] = False
    """True if media_image_url is accessible outside local network"""
    
    # App information
    app_id: Optional[str] = None
    """ID of current running app"""
    
    app_name: Optional[str] = None
    """Name of current running app"""
    
    # Group properties (for multi-room audio)
    group_members: Optional[list[str]] = None
    """List of player entities currently grouped together"""
    
    # Device classification
    device_class: Optional[str] = None
    """Type of media player: tv, speaker, receiver, etc."""
    
    # === Feature Support Flags ===
    # These determine which commands/features are available
    
    supports_play: bool = False
    """Player supports play command"""
    
    supports_pause: bool = False
    """Player supports pause command"""
    
    supports_stop: bool = False
    """Player supports stop command"""
    
    supports_seek: bool = False
    """Player supports seeking to specific position"""
    
    supports_volume_set: bool = False
    """Player supports setting volume level"""
    
    supports_volume_mute: bool = False
    """Player supports mute/unmute"""
    
    supports_previous_track: bool = False
    """Player supports previous track command"""
    
    supports_next_track: bool = False
    """Player supports next track command"""
    
    supports_shuffle_set: bool = False
    """Player supports setting shuffle mode"""
    
    supports_repeat_set: bool = False
    """Player supports setting repeat mode"""
    
    supports_turn_on: bool = False
    """Player supports turn on command"""
    
    supports_turn_off: bool = False
    """Player supports turn off command"""
    
    supports_play_media: bool = False
    """Player supports playing specific media (URLs, etc.)"""
    
    supports_volume_step: bool = False
    """Player supports volume up/down commands"""
    
    supports_select_source: bool = False
    """Player supports input source selection"""
    
    supports_select_sound_mode: bool = False
    """Player supports sound mode selection"""
    
    supports_clear_playlist: bool = False
    """Player supports clearing current playlist"""
    
    supports_browse_media: bool = False
    """Player supports media browsing"""


class MediaPlayer(Subscriber[MediaPlayerInfo]):
    """Enhanced MQTT media player with property-based state management"""
    
    def __init__(self, settings, command_callbacks=None, user_data=None):
        """Initialize MediaPlayer with automatic topic generation"""
        self._command_callbacks = command_callbacks or {}
        self._topics = {}
        
        # Generate topics based on supported features before calling super()
        self._generate_topics(settings)
        
        super().__init__(settings, self._command_callback_handler, user_data)
    
    def _generate_topics(self, settings):
        """Generate topics based on supported features and properties"""
        entity = settings.entity
        
        # Import here to avoid circular dependency
        from ha_mqtt_discoverable.utils import clean_string
        
        # Build entity topic with lowercase, dashified device name
        entity_topic = f"{entity.component}"
        if entity.device:
            device_name = clean_string(entity.device.name).lower()
            entity_topic += f"/{device_name}"
        entity_topic += f"/{clean_string(entity.name)}"
        
        state_prefix = settings.mqtt.state_prefix
        
        # Generate command topics based on supported features
        if entity.supports_play:
            self._topics['play'] = f"{state_prefix}/{entity_topic}/play"
        if entity.supports_pause:
            self._topics['pause'] = f"{state_prefix}/{entity_topic}/pause"
        if entity.supports_stop:
            self._topics['stop'] = f"{state_prefix}/{entity_topic}/stop"
        if entity.supports_next_track:
            self._topics['next'] = f"{state_prefix}/{entity_topic}/next"
        if entity.supports_previous_track:
            self._topics['previous'] = f"{state_prefix}/{entity_topic}/previous"
        if entity.supports_volume_set:
            self._topics['volumeset'] = f"{state_prefix}/{entity_topic}/volumeset"
        if entity.supports_seek:
            self._topics['seek'] = f"{state_prefix}/{entity_topic}/seek"
        if entity.supports_volume_mute:
            self._topics['mute'] = f"{state_prefix}/{entity_topic}/mute"
        if entity.supports_shuffle_set:
            self._topics['shuffle'] = f"{state_prefix}/{entity_topic}/shuffle"
        if entity.supports_repeat_set:
            self._topics['repeat'] = f"{state_prefix}/{entity_topic}/repeat"
        if entity.supports_select_source:
            self._topics['source'] = f"{state_prefix}/{entity_topic}/source"
        if entity.supports_select_sound_mode:
            self._topics['sound_mode'] = f"{state_prefix}/{entity_topic}/sound_mode"
        if entity.supports_turn_on:
            self._topics['turn_on'] = f"{state_prefix}/{entity_topic}/turn_on"
        if entity.supports_turn_off:
            self._topics['turn_off'] = f"{state_prefix}/{entity_topic}/turn_off"
        if entity.supports_play_media:
            self._topics['play_media'] = f"{state_prefix}/{entity_topic}/play_media"
        if entity.supports_browse_media:
            self._topics['browse_media'] = f"{state_prefix}/{entity_topic}/browse_media"
        
        # Generate state topics for properties that might be used
        self._topics['state'] = f"{state_prefix}/{entity_topic}/state"
        self._topics['title'] = f"{state_prefix}/{entity_topic}/title"
        self._topics['artist'] = f"{state_prefix}/{entity_topic}/artist"
        self._topics['album'] = f"{state_prefix}/{entity_topic}/album"
        self._topics['duration'] = f"{state_prefix}/{entity_topic}/duration"
        self._topics['position'] = f"{state_prefix}/{entity_topic}/position"
        self._topics['volume'] = f"{state_prefix}/{entity_topic}/volume"
        self._topics['albumart'] = f"{state_prefix}/{entity_topic}/albumart"
        self._topics['availability'] = f"{state_prefix}/{entity_topic}/availability"
    
    # === State Update Methods ===
    
    def set_state(self, state: str) -> None:
        """Update player state with validation"""
        valid_states = ['playing', 'paused', 'stopped', 'idle', 'off']
        if state not in valid_states:
            raise ValueError(f"Invalid state '{state}'. Must be one of: {valid_states}")
        
        self._entity.state = state
        logger.info(f"Setting {self._entity.name} state to {state}")
        self._state_helper(state, topic=self._topics['state'])
    
    def set_title(self, title: str) -> None:
        """Update media title"""
        self._entity.media_title = title
        logger.info(f"Setting {self._entity.name} title to {title}")
        self._state_helper(title, topic=self._topics['title'])
    
    def set_artist(self, artist: str) -> None:
        """Update media artist"""
        self._entity.media_artist = artist
        logger.info(f"Setting {self._entity.name} artist to {artist}")
        self._state_helper(artist, topic=self._topics['artist'])
    
    def set_album(self, album: str) -> None:
        """Update media album"""
        self._entity.media_album_name = album
        logger.info(f"Setting {self._entity.name} album to {album}")
        self._state_helper(album, topic=self._topics['album'])
    
    def set_volume(self, volume: float) -> None:
        """Update volume level with validation"""
        if not 0.0 <= volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {volume}")
        
        self._entity.volume_level = volume
        logger.info(f"Setting {self._entity.name} volume to {volume}")
        self._state_helper(str(volume), topic=self._topics['volume'])
    
    def set_position(self, position: int) -> None:
        """Update playback position"""
        if position < 0:
            raise ValueError("Position must be non-negative")
        if self._entity.media_duration and position > self._entity.media_duration:
            raise ValueError(f"Position {position} exceeds duration {self._entity.media_duration}")
        
        self._entity.media_position = position
        logger.info(f"Setting {self._entity.name} position to {position}")
        self._state_helper(str(position), topic=self._topics['position'])
    
    def set_duration(self, duration: int) -> None:
        """Update media duration"""
        if duration < 0:
            raise ValueError("Duration must be non-negative")
        
        self._entity.media_duration = duration
        logger.info(f"Setting {self._entity.name} duration to {duration}")
        self._state_helper(str(duration), topic=self._topics['duration'])
    
    def set_albumart_url(self, url: str) -> None:
        """Update album art URL"""
        self._entity.media_image_url = url
        logger.info(f"Setting {self._entity.name} album art URL to {url}")
        self._state_helper(url, topic=self._topics['albumart'])
    
    def set_muted(self, muted: bool) -> None:
        """Update mute state"""
        self._entity.is_volume_muted = muted
        logger.info(f"Setting {self._entity.name} muted to {muted}")
        # Note: mute state typically published to volume topic or separate mute topic
        # For now, we'll use a simple approach
    
    def set_shuffle(self, shuffle: bool) -> None:
        """Update shuffle state"""
        if not self._entity.supports_shuffle_set:
            raise RuntimeError("Player does not support shuffle control")
        
        self._entity.shuffle = shuffle
        logger.info(f"Setting {self._entity.name} shuffle to {shuffle}")
    
    def set_repeat(self, repeat: str) -> None:
        """Update repeat mode"""
        if not self._entity.supports_repeat_set:
            raise RuntimeError("Player does not support repeat control")
        
        valid_modes = ['off', 'all', 'one']
        if repeat not in valid_modes:
            raise ValueError(f"Invalid repeat mode '{repeat}'. Must be one of: {valid_modes}")
        
        self._entity.repeat = repeat
        logger.info(f"Setting {self._entity.name} repeat to {repeat}")
    
    def set_availability(self, available: bool) -> None:
        """Update entity availability"""
        message = "online" if available else "offline"
        logger.info(f"Setting {self._entity.name} availability to {message}")
        self.mqtt_client.publish(self._topics['availability'], message, retain=True)
    
    # === Bulk Update Methods ===
    
    def update_media_info(self, title=None, artist=None, album=None, duration=None, position=None, albumart_url=None):
        """Update multiple media properties at once"""
        if title is not None:
            self.set_title(title)
        if artist is not None:
            self.set_artist(artist)
        if album is not None:
            self.set_album(album)
        if duration is not None:
            self.set_duration(duration)
        if position is not None:
            self.set_position(position)
        if albumart_url is not None:
            self.set_albumart_url(albumart_url)
    
    def update_playback_state(self, state=None, volume=None, muted=None, shuffle=None, repeat=None):
        """Update multiple playback properties at once"""
        if state is not None:
            self.set_state(state)
        if volume is not None:
            self.set_volume(volume)
        if muted is not None:
            self.set_muted(muted)
        if shuffle is not None:
            self.set_shuffle(shuffle)
        if repeat is not None:
            self.set_repeat(repeat)
    
    # === Command Callback Handling ===
    
    def _command_callback_handler(self, client, user_data, message):
        """Enhanced command handler with better topic routing"""
        topic = message.topic
        
        try:
            payload = message.payload.decode()
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode payload for topic {topic}: {e}")
            return
        
        # Extract command from topic (last part after final slash)
        command_name = topic.split('/')[-1]
        
        # Route to appropriate callback
        callback_map = {
            'play': 'play',
            'pause': 'pause', 
            'stop': 'stop',
            'next': 'next',
            'previous': 'previous',
            'volumeset': 'volume_set',
            'seek': 'seek',
            'mute': 'mute',
            'shuffle': 'shuffle_set',
            'repeat': 'repeat_set',
            'source': 'select_source',
            'sound_mode': 'select_sound_mode',
            'turn_on': 'turn_on',
            'turn_off': 'turn_off',
            'play_media': 'play_media',
            'browse_media': 'browse_media'
        }
        
        callback_key = callback_map.get(command_name)
        if callback_key and callback_key in self._command_callbacks:
            try:
                parsed_payload = self._parse_command_payload(callback_key, payload)
                self._command_callbacks[callback_key](client, user_data, message, parsed_payload)
            except Exception as e:
                logger.error(f"Error executing callback for {callback_key}: {e}")
        else:
            logger.warning(f"No callback registered for command: {command_name}")
    
    def _parse_command_payload(self, command: str, payload: str):
        """Parse command payload based on command type"""
        if command in ['volume_set', 'seek']:
            try:
                return float(payload)
            except ValueError:
                logger.error(f"Invalid numeric payload for {command}: {payload}")
                return None
        elif command in ['shuffle_set', 'mute']:
            return payload.upper() == 'ON'
        else:
            return payload
    
    def generate_config(self) -> dict[str, Any]:
        """Generate discovery config based on supported features and properties"""
        config = super().generate_config()
        
        # Add supported features to config as Home Assistant features bitmask
        supported_features = []
        
        if self._entity.supports_play:
            supported_features.append('play')
        if self._entity.supports_pause:
            supported_features.append('pause')
        if self._entity.supports_stop:
            supported_features.append('stop')
        if self._entity.supports_seek:
            supported_features.append('seek')
        if self._entity.supports_volume_set:
            supported_features.append('volume_set')  
        if self._entity.supports_volume_mute:
            supported_features.append('volume_mute')
        if self._entity.supports_previous_track:
            supported_features.append('previous_track')
        if self._entity.supports_next_track:
            supported_features.append('next_track')
        if self._entity.supports_shuffle_set:
            supported_features.append('shuffle_set')
        if self._entity.supports_repeat_set:
            supported_features.append('repeat_set')
        if self._entity.supports_turn_on:
            supported_features.append('turn_on')
        if self._entity.supports_turn_off:
            supported_features.append('turn_off')
        if self._entity.supports_play_media:
            supported_features.append('play_media')
        if self._entity.supports_volume_step:
            supported_features.append('volume_step')
        if self._entity.supports_select_source:
            supported_features.append('select_source')
        if self._entity.supports_select_sound_mode:
            supported_features.append('select_sound_mode')
        if self._entity.supports_clear_playlist:
            supported_features.append('clear_playlist')
        if self._entity.supports_browse_media:
            supported_features.append('browse_media')
        
        # Add topics for supported features
        topics = {}
        
        # Add main state topic
        topics['state_topic'] = self._topics['state']
        
        # Add availability topic
        topics['availability_topic'] = self._topics['availability']
        topics['payload_available'] = 'online'
        topics['payload_not_available'] = 'offline'
        
        # Add metadata topics
        topics['media_title_topic'] = self._topics['title']
        topics['media_artist_topic'] = self._topics['artist']
        topics['media_album_name_topic'] = self._topics['album']
        topics['media_duration_topic'] = self._topics['duration']
        topics['media_position_topic'] = self._topics['position']
        topics['volume_level_topic'] = self._topics['volume']
        topics['media_image_url_topic'] = self._topics['albumart']
        
        # Add command topics for supported features
        if self._entity.supports_play:
            topics['play_topic'] = self._topics['play']
        if self._entity.supports_pause:
            topics['pause_topic'] = self._topics['pause']
        if self._entity.supports_stop:
            topics['stop_topic'] = self._topics['stop']
        if self._entity.supports_next_track:
            topics['next_topic'] = self._topics['next']
        if self._entity.supports_previous_track:
            topics['previous_topic'] = self._topics['previous']
        if self._entity.supports_volume_set:
            topics['volume_set_topic'] = self._topics['volumeset']
        if self._entity.supports_seek:
            topics['seek_topic'] = self._topics['seek']
        
        return config | topics


>>>>>>> 04ae7e8 (Trailing newline)
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
        logger.info(f"Setting {self._entity.name} to {state_message} using {self.state_topic}")
        self._state_helper(state=state_message)


class Sensor(Discoverable[SensorInfo]):
    def set_state(self, state: str | int | float, last_reset: str = None) -> None:
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


# Inherit the on and off methods from the BinarySensor class, changing only the
# documentation string
class Switch(Subscriber[SwitchInfo], BinarySensor):
    """Implements an MQTT switch:
    https://www.home-assistant.io/integrations/switch.mqtt
    """

    def off(self):
        """
        Set switch to off
        """
        super().off()

    def on(self):
        """
        Set switch to on
        """
        super().on()


class Light(Subscriber[LightInfo]):
    """Implements an MQTT light.
    https://www.home-assistant.io/integrations/light.mqtt
    """

    def on(self) -> None:
        """
        Set light to on
        """
        state_payload = {
            "state": self._entity.payload_on,
        }
        self._update_state(state_payload)

    def off(self) -> None:
        """
        Set light to off
        """
        state_payload = {
            "state": self._entity.payload_off,
        }
        self._update_state(state_payload)

    def brightness(self, brightness: int) -> None:
        """
        Set brightness of the light

        Args:
            brightness(int): Brightness value of [0,255]
        """
        if brightness < 0 or brightness > 255:
            raise RuntimeError(f"Brightness for light {self._entity.name} is out of range")

        state_payload = {
            "brightness": brightness,
            "state": self._entity.payload_on,
        }

        self._update_state(state_payload)

    def color(self, color_mode: str, color: dict[str, Any]) -> None:
        """
        Set color of the light.
        NOTE: Make sure color formatting conforms to color mode, it is up to the caller to make sure
        of this. Also, make sure the color mode is in the list supported_color_modes

        Args:
            color_mode(str): A valid color mode
            color(Dict[str, Any]): Color to set, according to color_mode format
        """
        if not self._entity.color_mode:
            raise RuntimeError(f"Light {self._entity.name} does not support setting color")
        if color_mode not in self._entity.supported_color_modes:
            raise RuntimeError(f"Color is not in configured supported_color_modes {str(self._entity.supported_color_modes)}")
        # We do not check if color schema conforms to color mode formatting, it is up to the caller
        state_payload = {
            "color_mode": color_mode,
            "color": color,
            "state": self._entity.payload_on,
        }
        self._update_state(state_payload)

    def effect(self, effect: str) -> None:
        """
        Enable effect of the light

        Args:
            effect(str): Effect to apply
        """
        if not self._entity.effect:
            raise RuntimeError(f"Light {self._entity.name} does not support effects")
        if effect not in self._entity.effect_list:
            raise RuntimeError(f"Effect is not within configured effect_list {str(self._entity.effect_list)}")
        state_payload = {
            "effect": effect,
            "state": self._entity.payload_on,
        }
        self._update_state(state_payload)

    def _update_state(self, state: dict[str, Any]) -> None:
        """
        Update MQTT sensor state

        Args:
            state(Dict[str, Any]): What state to set the light to
        """
        logger.info(f"Setting {self._entity.name} to {state} using {self.state_topic}")
        json_state = json.dumps(state)
        self._state_helper(state=json_state, topic=self.state_topic, retain=self._entity.retain)


class Cover(Subscriber[CoverInfo]):
    """Implements an MQTT cover:
    https://www.home-assistant.io/integrations/cover.mqtt
    """

    def open(self) -> None:
        """Set cover state to open"""
        self._update_state(self._entity.state_open)

    def closed(self) -> None:
        """Set cover state to closed"""
        self._update_state(self._entity.state_closed)

    def closing(self) -> None:
        """Set cover state to closing"""
        self._update_state(self._entity.state_closing)

    def opening(self) -> None:
        """Set cover state to opening"""
        self._update_state(self._entity.state_opening)

    def stopped(self) -> None:
        """Set cover state to stopped"""
        self._update_state(self._entity.state_stopped)

    def _update_state(self, state: str) -> None:
        """
        Update MQTT sensor state

        Args:
            state(str): What state to set the cover to
        """
        print("State: " + state)
        logger.info(f"Setting {self._entity.name} to {state} using {self.state_topic}")
        self._state_helper(state=state, topic=self.state_topic, retain=self._entity.retain)


class Button(Subscriber[ButtonInfo]):
    """Implements an MQTT button:
    https://www.home-assistant.io/integrations/button.mqtt
    """


class DeviceTrigger(Discoverable[DeviceTriggerInfo]):
    """Implements an MQTT Device Trigger
    https://www.home-assistant.io/integrations/device_trigger.mqtt/
    """

    def generate_config(self) -> dict[str, Any]:
        """Publish a custom configuration: since this entity does not provide a
        `state_topic`, HA expects a `topic` key in the config
        """
        config = super().generate_config()
        # Publish our `state_topic` as `topic`
        topics = {
            "topic": self.state_topic,
        }
        return config | topics

    def trigger(self, payload: Optional[str] = None):
        """
        Generate a device trigger event

        Args:
            payload: custom payload to send in the trigger topic

        """
        return self._state_helper(payload, self.state_topic, retain=False)


class Text(Subscriber[TextInfo]):
    """Implements an MQTT text:
    https://www.home-assistant.io/integrations/text.mqtt/
    """

    def set_text(self, text: str) -> None:
        """
        Update the text displayed by this sensor. Check that it is of acceptable length.

        Args:
            text(str): Value of the text configured for this entity
        """
        if not self._entity.min <= len(text) <= self._entity.max:
            bound = f"[{self._entity.min}, {self._entity.max}]"
            raise RuntimeError(f"Text is not within configured length boundaries {bound}")

        logger.info(f"Setting {self._entity.name} to {text} using {self.state_topic}")
        self._state_helper(str(text))


class Number(Subscriber[NumberInfo]):
    """Implements an MQTT number:
    https://www.home-assistant.io/integrations/number.mqtt/
    """

    def set_value(self, value: float) -> None:
        """
        Update the numeric value. Raises an error if not within the acceptable range.

        Args:
            value(str): Value of the number configured for this entity
        """
        if not self._entity.min <= value <= self._entity.max:
            bound = f"[{self._entity.min}, {self._entity.max}]"
            raise RuntimeError(f"Value is not within configured boundaries {bound}")

        logger.info(f"Setting {self._entity.name} to {value} using {self.state_topic}")
        self._state_helper(value)


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

        logger.info(f"Publishing camera image topic {image_topic} to {self._entity.topic}")
        self._state_helper(image_topic)

    def set_availability(self, available: bool) -> None:
        """
        Update the camera availability status.

        Args:
            available (bool): Whether the camera is available or not.
        """
        payload = self._entity.payload_available if available else self._entity.payload_not_available
        logger.info(f"Setting camera availability to {payload} using {self._entity.availability_topic}")
        self.mqtt_client.publish(self._entity.availability_topic, payload, retain=self._entity.retain)


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


class Select(Subscriber[SelectInfo]):
    """
    Implements an MQTT select for Home Assistant MQTT discovery:
    https://www.home-assistant.io/integrations/select.mqtt/
    """

    def set_options(self, opt: list) -> None:
        """
        Update the selectable options.

        Args:
            opt (list): List of options that can be selected.
        """
        if not opt:
            raise RuntimeError("Image URL cannot be empty")

        logger.info(f"Publishing options {opt} to {self._entity.options}")
        self._state_helper(opt)


class Update(Subscriber[UpdateInfo]):
    """
    Implements an MQTT update for Home Assistant MQTT discovery:
    https://www.home-assistant.io/integrations/update.mqtt/

    This class provides support for Home Assistant Update entities, allowing you to:
    1. Post update availability information
    2. Automatically register with Home Assistant via MQTT discovery
    3. Receive install command callbacks from Home Assistant
    4. Track installation progress with percentage updates

    Example:
        Basic usage with device context:

        >>> from ha_mqtt_discoverable import Settings, DeviceInfo
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
        >>> # Create update entity info
        >>> update_info = UpdateInfo(
        ...     name="firmware_update",
        ...     device=device,
        ...     unique_id="device_123_firmware",
        ...     title="Device Firmware",
        ...     device_class="firmware"
        ... )
        >>>
        >>> # Setup MQTT settings
        >>> mqtt_settings = Settings.MQTT(host="localhost")
        >>> settings = Settings(mqtt=mqtt_settings, entity=update_info)
        >>>
        >>> # Define install callback
        >>> def handle_install(client, user_data, message):
        ...     print("Install command received!")
        ...     # Start your update process here
        ...     update.set_progress(0)
        ...     # ... perform update ...
        ...     update.set_progress(100)
        >>>
        >>> # Create update entity
        >>> update = Update(settings, handle_install)
        >>>
        >>> # Set current and available versions
        >>> update.set_installed_version("1.2.3")
        >>> update.set_latest_version("1.2.4")
        >>>
        >>> # Simple state (publishes string): no update available
        >>> update.set_state("1.2.3")
        >>>
        >>> # Complex state (publishes JSON): update available or in progress
        >>> update.set_state("1.2.3", "1.2.4", in_progress=True, progress=50)
    """

    def __init__(self, settings, command_callback, user_data=None):
        """
        Initialize the Update entity.

        Args:
            settings: Settings for the entity
            command_callback: Callback function invoked when install command is received
            user_data: Optional user data passed to the callback
        """
        super().__init__(settings, command_callback, user_data)

        # Set up latest version topic if configured
        if self._entity.latest_version_topic:
            self._latest_version_topic = self._entity.latest_version_topic
        else:
            self._latest_version_topic = f"{self._settings.mqtt.state_prefix}/{self._entity_topic}/latest_version"

    def set_installed_version(self, version: str) -> None:
        """
        Update the installed version.

        Args:
            version: The currently installed version
        """
        logger.info(f"Setting installed version for {self._entity.name} to {version}")
        self._state_helper(version)

    def set_latest_version(self, version: str) -> None:
        """
        Update the latest available version.

        Args:
            version: The latest available version
        """
        logger.info(f"Setting latest version for {self._entity.name} to {version}")
        self._state_helper(version, topic=self._latest_version_topic)

    def set_progress(self, progress: int) -> None:
        """
        Update the installation progress.

        Args:
            progress: Progress percentage (0-100)
        """
        if not 0 <= progress <= 100:
            raise ValueError(f"Progress must be between 0 and 100, got {progress}")

        state: dict[str, bool | int] = {"in_progress": True, "update_percentage": progress}
        logger.info(f"Setting update progress for {self._entity.name} to {progress}%")
        self._update_state(state)

    def set_state(
        self, *, installed: str, latest: str | None = None, in_progress: bool = False, progress: int | None = None
    ) -> None:
        """
        Update the complete update state.

        All arguments are keyword-only to prevent confusion.

        Args:
            installed: Currently installed version
            latest: Latest available version (optional)
            in_progress: Whether an update is currently in progress
            progress: Update progress percentage (0-100, optional)

        Example:
            update.set_state(installed="1.0.0", latest="1.1.0")
            update.set_state(installed="1.0.0", latest="1.1.0", in_progress=True, progress=50)
        """
        # If only installed version is provided, publish as simple string
        if latest is None and not in_progress and progress is None:
            logger.info(f"Setting installed version for {self._entity.name} to {installed}")
            self._update_state(installed)
            return

        # Otherwise, publish as JSON object
        state: dict[str, str | bool | int] = {"installed_version": installed}

        if latest is not None:
            state["latest_version"] = latest

        if in_progress:
            state["in_progress"] = True

        if progress is not None:
            if not 0 <= progress <= 100:
                raise ValueError(f"Progress must be between 0 and 100, got {progress}")
            state["update_percentage"] = progress

        logger.info(f"Setting complete state for {self._entity.name}: {state}")
        self._update_state(state)

    def _update_state(self, state: dict[str, str | bool | int] | str) -> None:
        """
        Update MQTT entity state.

        Args:
            state: State to publish (dict for JSON or str for simple value)
        """
        if isinstance(state, dict):
            json_state = json.dumps(state)
            self._state_helper(json_state)
        else:
            self._state_helper(state)

    def generate_config(self) -> dict[str, Any]:
        """Override base config to add update-specific topics"""
        config = super().generate_config()

        # Add update-specific topics
        topics = {}
        if hasattr(self, "_latest_version_topic"):
            topics["latest_version_topic"] = self._latest_version_topic

        # Add payload_install
        topics["payload_install"] = self._entity.payload_install

        return config | topics
