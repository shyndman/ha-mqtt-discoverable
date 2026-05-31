import json
import logging
from collections.abc import Callable
from enum import Enum
from typing import ClassVar, TypedDict, final, override

from paho.mqtt.client import Client, MQTTMessage
from pydantic import BaseModel, ValidationError

from ha_mqtt_discoverable._base import Discoverable
from ha_mqtt_discoverable._media_player_manifest import (
    MEDIA_PLAYER_TOPIC_SPECS,
    MEDIA_PLAYER_TOPIC_SPECS_BY_NAME,
    MediaPlayerCallbackStyle,
    MediaPlayerPayloadParser,
    MediaPlayerTopicSpec,
)
from ha_mqtt_discoverable._models import EntityInfo, Settings
from ha_mqtt_discoverable._topic_paths import build_entity_topic, build_state_topic

logger = logging.getLogger(__name__)


def _topic_name(name: str) -> str:
    return MEDIA_PLAYER_TOPIC_SPECS_BY_NAME[name].topic


# === Pydantic Payload Models ===


class RepeatMode(str, Enum):
    """Valid repeat modes for media players"""

    OFF = "off"
    ALL = "all"
    ONE = "one"


class PlayMediaPayload(BaseModel):
    """Payload structure for play_media commands"""

    media_type: str
    media_id: str
    enqueue: str | None = None  # "add", "next", "play", "replace"
    announce: bool | None = None


# === Type Aliases for Callbacks ===

# Simple command callbacks (no payload needed)
type CommandCallback = Callable[[Client, object, MQTTMessage], None]

# Payload-based callbacks (parsed payload first)
type FloatCallback = Callable[[float, Client, object, MQTTMessage], None]
type BoolCallback = Callable[[bool, Client, object, MQTTMessage], None]
type SelectionCallback = Callable[[str, Client, object, MQTTMessage], None]
type RepeatCallback = Callable[[RepeatMode, Client, object, MQTTMessage], None]
type PlayMediaCallback = Callable[[PlayMediaPayload, Client, object, MQTTMessage], None]
type ParsedCommandPayload = float | bool | str | RepeatMode | PlayMediaPayload | None


# Topic name constants
@final
class MediaPlayerTopics:
    """Symbolic constants for media player MQTT topic names"""

    PLAY: ClassVar[str] = _topic_name("play")
    PAUSE: ClassVar[str] = _topic_name("pause")
    STOP: ClassVar[str] = _topic_name("stop")
    NEXT_TRACK: ClassVar[str] = _topic_name("next_track")
    PREVIOUS_TRACK: ClassVar[str] = _topic_name("previous_track")
    VOLUME_SET: ClassVar[str] = _topic_name("volume_set")
    SEEK: ClassVar[str] = _topic_name("seek")
    VOLUME_MUTE: ClassVar[str] = _topic_name("volume_mute")
    SHUFFLE_SET: ClassVar[str] = _topic_name("shuffle_set")
    REPEAT_SET: ClassVar[str] = _topic_name("repeat_set")
    SELECT_SOURCE: ClassVar[str] = _topic_name("select_source")
    SELECT_SOUND_MODE: ClassVar[str] = _topic_name("select_sound_mode")
    TURN_ON: ClassVar[str] = _topic_name("turn_on")
    TURN_OFF: ClassVar[str] = _topic_name("turn_off")
    PLAY_MEDIA: ClassVar[str] = _topic_name("play_media")
    BROWSE_MEDIA: ClassVar[str] = _topic_name("browse_media")

    # State topics
    STATE: ClassVar[str] = _topic_name("state")
    TITLE: ClassVar[str] = _topic_name("title")
    ARTIST: ClassVar[str] = _topic_name("artist")
    ALBUM: ClassVar[str] = _topic_name("album")
    DURATION: ClassVar[str] = _topic_name("duration")
    POSITION: ClassVar[str] = _topic_name("position")
    VOLUME: ClassVar[str] = _topic_name("volume")
    ALBUMART: ClassVar[str] = _topic_name("albumart")
    MEDIA_IMAGE_REMOTELY_ACCESSIBLE: ClassVar[str] = _topic_name(
        "media_image_remotely_accessible"
    )
    AVAILABILITY: ClassVar[str] = _topic_name("availability")


class MediaPlayerCallbacks(TypedDict, total=False):
    """Type-safe callback definitions for media player commands"""

    # Simple command callbacks (no payload needed)
    play: CommandCallback
    pause: CommandCallback
    stop: CommandCallback
    next_track: CommandCallback
    previous_track: CommandCallback
    turn_on: CommandCallback
    turn_off: CommandCallback
    browse_media: CommandCallback

    # Payload-based callbacks (parsed payload first)
    volume_set: FloatCallback
    seek: FloatCallback
    shuffle_set: BoolCallback
    volume_mute: BoolCallback
    repeat_set: RepeatCallback
    select_source: SelectionCallback
    select_sound_mode: SelectionCallback
    play_media: PlayMediaCallback


class MediaPlayerInfo(EntityInfo):
    """Media Player configuration for Home Assistant MQTT discovery"""

    component: str = "media_player"

    # === Configuration Properties ===

    # Volume configuration
    volume_step: float | None = 0.1
    """Volume step for volume_up/volume_down commands"""

    # Available options (for configuration/discovery)
    source_list: list[str] | None = None
    """List of available input sources"""

    sound_mode_list: list[str] | None = None
    """List of available sound modes"""

    # Device classification
    device_class: str | None = None
    """Type of media player: tv, speaker, receiver, etc."""


class MediaPlayer(Discoverable[MediaPlayerInfo]):
    """Enhanced MQTT media player with property-based state management"""

    _callbacks: MediaPlayerCallbacks
    _topics: dict[str, str]
    _command_topics_by_path: dict[str, MediaPlayerTopicSpec]

    def __init__(
        self,
        settings: Settings[MediaPlayerInfo],
        callbacks: MediaPlayerCallbacks,
        user_data: object | None = None,
    ) -> None:
        """
        Initialize MediaPlayer with callbacks determining supported features.

        Args:
            settings: MQTT and entity configuration settings
            callbacks: Dict of command callbacks - presence determines which features are supported
            user_data: Optional user data (unused but kept for compatibility)

        Note:
            Topics must be generated before calling super().__init__() because the
            _on_client_connected callback needs access to self._topics for subscription.
        """
        logger.debug(
            f"Initializing MediaPlayer '{settings.entity.name}' with callbacks: {list(callbacks.keys())}"
        )
        self._callbacks = callbacks
        self._topics = {}
        self._command_topics_by_path = {}

        # Generate topics based on provided callbacks before calling super()
        # This is required because _on_client_connected needs self._topics
        self._generate_topics(settings)
        logger.debug(
            f"Generated {len(self._topics)} topics for MediaPlayer '{settings.entity.name}'"
        )

        super().__init__(settings, self._on_client_connected)

        # Set up message callback for all subscribed topics
        self.mqtt_client.on_message = self._command_callback_handler
        logger.debug(f"MediaPlayer '{settings.entity.name}' initialization complete")

        self._connect_client()

    def _on_client_connected(self, client: Client, *_args: object) -> None:
        """Subscribe to all command topics based on provided callbacks"""
        logger.debug(
            f"MQTT client connected for MediaPlayer '{self._entity.name}', subscribing to command topics"
        )
        subscribed_count = 0
        for topic_url, spec in self._command_topics_by_path.items():
            logger.debug(f"Subscribing to command topic '{spec.topic}': {topic_url}")
            result, _ = client.subscribe(topic_url, qos=1)
            if result != 0:  # mqtt.MQTT_ERR_SUCCESS
                logger.error(f"Error subscribing to MQTT command topic: {topic_url}")
            else:
                subscribed_count += 1
        logger.debug(
            f"Successfully subscribed to {subscribed_count} command topics for MediaPlayer '{self._entity.name}'"
        )

    def _generate_topics(self, settings: Settings[MediaPlayerInfo]) -> None:
        """Generate topics based on supported features and properties"""
        entity = settings.entity
        logger.debug(
            f"Generating topics for MediaPlayer '{entity.name}' with {len(self._callbacks)} callbacks"
        )

        entity_topic = build_entity_topic(entity)
        state_prefix = settings.mqtt.state_prefix
        logger.debug(f"Using base entity topic: {state_prefix}/{entity_topic}")
        command_topics_generated = 0
        state_topics_generated = 0

        for spec in MEDIA_PLAYER_TOPIC_SPECS:
            if not spec.always_include and spec.topic not in self._callbacks:
                continue

            topic_url = build_state_topic(state_prefix, entity_topic, spec.topic)
            self._topics[spec.topic] = topic_url

            if spec.is_command:
                self._command_topics_by_path[topic_url] = spec
                command_topics_generated += 1
            else:
                state_topics_generated += 1

        logger.debug(
            f"Total topics generated for MediaPlayer '{entity.name}': {len(self._topics)} ({command_topics_generated} command + {state_topics_generated} state)"
        )

    # === State Update Methods ===

    def set_state(self, state: str) -> None:
        """Update player state with validation"""
        valid_states = ["playing", "paused", "stopped", "idle", "off"]
        if state not in valid_states:
            raise ValueError(f"Invalid state '{state}'. Must be one of: {valid_states}")

        logger.info(f"Setting {self._entity.name} state to {state}")
        self._state_helper(state, topic=self._topics["state"])

    def set_title(self, title: str) -> None:
        """Update media title"""
        logger.info(f"Setting {self._entity.name} title to {title}")
        self._state_helper(title, topic=self._topics["title"])

    def set_artist(self, artist: str) -> None:
        """Update media artist"""
        logger.info(f"Setting {self._entity.name} artist to {artist}")
        self._state_helper(artist, topic=self._topics["artist"])

    def set_album(self, album: str) -> None:
        """Update media album"""
        logger.info(f"Setting {self._entity.name} album to {album}")
        self._state_helper(album, topic=self._topics["album"])

    def set_volume(self, volume: float) -> None:
        """Update volume level with validation"""
        if not 0.0 <= volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {volume}")

        logger.info(f"Setting {self._entity.name} volume to {volume}")
        self._state_helper(str(volume), topic=self._topics["volume"])

    def set_position(self, position: int) -> None:
        """Update playback position"""
        if position < 0:
            raise ValueError("Position must be non-negative")

        logger.info(f"Setting {self._entity.name} position to {position}")
        self._state_helper(str(position), topic=self._topics["position"])

    def set_duration(self, duration: int) -> None:
        """Update media duration"""
        if duration < 0:
            raise ValueError("Duration must be non-negative")

        logger.info(f"Setting {self._entity.name} duration to {duration}")
        self._state_helper(str(duration), topic=self._topics["duration"])

    def set_albumart_url(self, url: str) -> None:
        """Update album art URL"""
        logger.info(f"Setting {self._entity.name} album art URL to {url}")
        self._state_helper(url, topic=self._topics["albumart"])

    def set_media_image_remotely_accessible(self, accessible: bool) -> None:
        """Update whether media image URL is accessible outside the home network"""
        message = "true" if accessible else "false"
        logger.info(
            f"Setting {self._entity.name} media image remotely accessible to {message}"
        )
        self._state_helper(
            message, topic=self._topics["media_image_remotely_accessible"]
        )

    def set_muted(self, muted: bool) -> None:
        """Update mute state"""
        logger.info(f"Setting {self._entity.name} muted to {muted}")
        # TODO: This currently validates/logs only and does not publish state.
        # Note: mute state typically published to volume topic or separate mute topic
        # For now, we'll use a simple approach

    def set_shuffle(self, shuffle: bool) -> None:
        """Update shuffle state"""
        if MediaPlayerTopics.SHUFFLE_SET not in self._topics:
            raise RuntimeError("Player does not support shuffle control")

        logger.info(f"Setting {self._entity.name} shuffle to {shuffle}")
        # TODO: This currently validates/logs only and does not publish state.

    def set_repeat(self, repeat: str) -> None:
        """Update repeat mode"""
        if MediaPlayerTopics.REPEAT_SET not in self._topics:
            raise RuntimeError("Player does not support repeat control")

        valid_modes = ["off", "all", "one"]
        if repeat not in valid_modes:
            raise ValueError(
                f"Invalid repeat mode '{repeat}'. Must be one of: {valid_modes}"
            )

        logger.info(f"Setting {self._entity.name} repeat to {repeat}")
        # TODO: This currently validates/logs only and does not publish state.

    @override
    def set_availability(self, availability: bool) -> None:
        """Update entity availability"""
        message = "online" if availability else "offline"
        logger.info(f"Setting {self._entity.name} availability to {message}")
        self.mqtt_client.publish(self._topics["availability"], message, retain=True)

    # === Bulk Update Methods ===

    def update_media_info(
        self,
        title: str,
        duration: int,
        artist: str | None = None,
        album: str | None = None,
        albumart_url: str | None = None,
        media_image_remotely_accessible: bool | None = None,
    ) -> None:
        """Update media properties, clearing all fields first then setting provided values"""
        # Prepare final values - use empty strings/zero for clearing, or provided values
        final_title = title
        final_duration = duration
        final_artist = artist if artist is not None else ""
        final_album = album if album is not None else ""
        final_albumart_url = albumart_url if albumart_url is not None else ""
        final_media_image_remotely_accessible = (
            media_image_remotely_accessible
            if media_image_remotely_accessible is not None
            else False
        )

        # Set all values once
        self.set_title(final_title)
        self.set_duration(final_duration)
        self.set_artist(final_artist)
        self.set_album(final_album)
        self.set_albumart_url(final_albumart_url)
        self.set_media_image_remotely_accessible(final_media_image_remotely_accessible)

    def update_playback_state(
        self,
        state: str | None = None,
        volume: float | None = None,
        muted: bool | None = None,
        shuffle: bool | None = None,
        repeat: str | None = None,
    ) -> None:
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

    def _command_callback_handler(
        self, client: Client, user_data: object, message: MQTTMessage
    ) -> None:
        """Command handler that routes MQTT messages to appropriate callbacks"""
        topic = message.topic
        logger.debug(f"Received MQTT message on topic: {topic}")

        try:
            payload = message.payload.decode()
            logger.debug(f"Decoded payload: {payload}")
        except UnicodeDecodeError:
            logger.exception(f"Failed to decode payload for topic {topic}")
            return

        spec = self._command_topics_by_path.get(topic)
        if spec is None:
            logger.warning(f"No command registered for topic: {topic}")
            return

        command_name = spec.topic
        logger.debug(f"Extracted command name: {command_name}")

        # Exit early if no callback registered
        if command_name not in self._callbacks:
            logger.warning(f"No callback registered for command: {command_name}")
            return

        if spec.callback_style is MediaPlayerCallbackStyle.SIMPLE:
            logger.debug(f"Invoking simple command callback for: {command_name}")
            self._callbacks[command_name](client, user_data, message)
        else:
            # Payload-based commands need parsing
            parsed_payload = self._parse_command_payload(command_name, payload)
            logger.debug(f"Parsed payload for {command_name}: {parsed_payload}")
            logger.debug(f"Invoking payload-based callback for command: {command_name}")
            self._callbacks[command_name](parsed_payload, client, user_data, message)

        logger.debug(f"Successfully executed callback for {command_name}")

    def _parse_command_payload(
        self, command: str, payload: str
    ) -> ParsedCommandPayload:
        """Parse command payload based on command type"""
        logger.debug(f"Parsing payload for command '{command}': {payload}")

        spec = MEDIA_PLAYER_TOPIC_SPECS_BY_NAME.get(command)
        if spec is None:
            logger.debug(
                f"Using string payload for unknown command {command}: {payload}"
            )
            return payload

        match spec.payload_parser:
            case MediaPlayerPayloadParser.FLOAT:
                try:
                    parsed_value = float(payload)
                    logger.debug(f"Parsed float payload for {command}: {parsed_value}")
                    return parsed_value
                except ValueError:
                    logger.exception(f"Invalid float payload for {command}: {payload}")
                    return None

            case MediaPlayerPayloadParser.BOOL_ON_OFF:
                parsed_value = payload.upper() == "ON"
                logger.debug(
                    f"Parsed boolean payload for {command}: {parsed_value} (from '{payload}')"
                )
                return parsed_value

            case MediaPlayerPayloadParser.REPEAT_MODE:
                try:
                    repeat_mode = RepeatMode(payload)
                    logger.debug(f"Parsed repeat mode for {command}: {repeat_mode}")
                    return repeat_mode
                except ValueError:
                    logger.exception(
                        f"Invalid repeat mode for {command}: {payload}. Valid modes: {[mode.value for mode in RepeatMode]}"
                    )
                    return None

            case MediaPlayerPayloadParser.PLAY_MEDIA_JSON:
                try:
                    play_media_payload = PlayMediaPayload.model_validate_json(payload)
                    logger.debug(
                        f"Parsed play_media JSON for {command}: {play_media_payload}"
                    )
                    return play_media_payload
                except (json.JSONDecodeError, ValidationError):
                    logger.exception(f"Invalid play_media payload for {command}")
                    return None

            case _:
                logger.debug(f"Using string payload for {command}: {payload}")
                return payload

    @override
    def generate_config(self) -> dict[str, object]:
        """Generate discovery config based on available topics"""
        logger.debug(
            f"Generating Home Assistant discovery config for MediaPlayer '{self._entity.name}'"
        )
        config = super().generate_config()

        topic_config: dict[str, object] = {}
        logger.debug(f"Starting with base config keys: {list(config.keys())}")
        logger.debug(f"Processing {len(self._topics)} topics for config generation")

        for spec in MEDIA_PLAYER_TOPIC_SPECS:
            topic_url = self._topics.get(spec.topic)
            if topic_url is None:
                continue

            topic_config[spec.config_key] = topic_url
            logger.debug(f"Added topic '{spec.config_key}': {topic_url}")

            if spec.adds_availability_payloads:
                topic_config["payload_available"] = "online"
                topic_config["payload_not_available"] = "offline"

        final_config = config | topic_config
        logger.debug(
            f"Generated complete config for MediaPlayer '{self._entity.name}': {len(final_config)} total keys ({len(config)} base + {len(topic_config)} topics)"
        )
        logger.debug(f"Config topic keys: {list(topic_config.keys())}")
        return final_config
