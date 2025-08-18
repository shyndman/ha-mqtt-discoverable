import logging
from collections.abc import Callable
from enum import Enum
from typing import TypedDict

from paho.mqtt.client import Client, MQTTMessage
from pydantic import BaseModel

from ha_mqtt_discoverable import Discoverable, EntityInfo

logger = logging.getLogger(__name__)


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


# Topic name constants
class MediaPlayerTopics:
    """Symbolic constants for media player MQTT topic names"""

    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    NEXT_TRACK = "next_track"
    PREVIOUS_TRACK = "previous_track"
    VOLUME_SET = "volume_set"
    SEEK = "seek"
    VOLUME_MUTE = "volume_mute"
    SHUFFLE_SET = "shuffle_set"
    REPEAT_SET = "repeat_set"
    SELECT_SOURCE = "select_source"
    SELECT_SOUND_MODE = "select_sound_mode"
    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    PLAY_MEDIA = "play_media"
    BROWSE_MEDIA = "browse_media"

    # State topics
    STATE = "state"
    TITLE = "title"
    ARTIST = "artist"
    ALBUM = "album"
    DURATION = "duration"
    POSITION = "position"
    VOLUME = "volume"
    ALBUMART = "albumart"
    MEDIA_IMAGE_REMOTELY_ACCESSIBLE = "media_image_remotely_accessible"
    AVAILABILITY = "availability"


# Command topics that require MQTT subscription
COMMAND_TOPICS = {
    MediaPlayerTopics.PLAY,
    MediaPlayerTopics.PAUSE,
    MediaPlayerTopics.STOP,
    MediaPlayerTopics.NEXT_TRACK,
    MediaPlayerTopics.PREVIOUS_TRACK,
    MediaPlayerTopics.VOLUME_SET,
    MediaPlayerTopics.SEEK,
    MediaPlayerTopics.VOLUME_MUTE,
    MediaPlayerTopics.SHUFFLE_SET,
    MediaPlayerTopics.REPEAT_SET,
    MediaPlayerTopics.SELECT_SOURCE,
    MediaPlayerTopics.SELECT_SOUND_MODE,
    MediaPlayerTopics.TURN_ON,
    MediaPlayerTopics.TURN_OFF,
    MediaPlayerTopics.PLAY_MEDIA,
    MediaPlayerTopics.BROWSE_MEDIA,
}

# Simple commands that don't need payload parsing
_SIMPLE_COMMANDS = {
    MediaPlayerTopics.PLAY,
    MediaPlayerTopics.PAUSE,
    MediaPlayerTopics.STOP,
    MediaPlayerTopics.NEXT_TRACK,
    MediaPlayerTopics.PREVIOUS_TRACK,
    MediaPlayerTopics.TURN_ON,
    MediaPlayerTopics.TURN_OFF,
    MediaPlayerTopics.BROWSE_MEDIA,
}


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

    def __init__(self, settings, callbacks: MediaPlayerCallbacks, user_data=None):
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
        logger.debug(f"Initializing MediaPlayer '{settings.entity.name}' with callbacks: {list(callbacks.keys())}")
        self._callbacks = callbacks
        self._topics = {}

        # Generate topics based on provided callbacks before calling super()
        # This is required because _on_client_connected needs self._topics
        self._generate_topics(settings)
        logger.debug(f"Generated {len(self._topics)} topics for MediaPlayer '{settings.entity.name}'")

        super().__init__(settings, self._on_client_connected)

        # Set up message callback for all subscribed topics
        self.mqtt_client.on_message = self._command_callback_handler
        logger.debug(f"MediaPlayer '{settings.entity.name}' initialization complete")

        self._connect_client()

    def _on_client_connected(self, client, *args):
        """Subscribe to all command topics based on provided callbacks"""
        logger.debug(f"MQTT client connected for MediaPlayer '{self._entity.name}', subscribing to command topics")
        subscribed_count = 0
        for topic_key, topic_url in self._topics.items():
            # Only subscribe to command topics (not state topics)
            if topic_key in COMMAND_TOPICS:
                logger.debug(f"Subscribing to command topic '{topic_key}': {topic_url}")
                result, _ = client.subscribe(topic_url, qos=1)
                if result != 0:  # mqtt.MQTT_ERR_SUCCESS
                    logger.error(f"Error subscribing to MQTT command topic: {topic_url}")
                else:
                    subscribed_count += 1
        logger.debug(f"Successfully subscribed to {subscribed_count} command topics for MediaPlayer '{self._entity.name}'")

    def _generate_topics(self, settings):
        """Generate topics based on supported features and properties"""
        entity = settings.entity
        logger.debug(f"Generating topics for MediaPlayer '{entity.name}' with {len(self._callbacks)} callbacks")

        # Import here to avoid circular dependency
        from ha_mqtt_discoverable.utils import clean_string

        # Build entity topic with lowercase, dashified device name
        entity_topic = f"{entity.component}"
        if entity.device:
            device_name = clean_string(entity.device.name)
            entity_topic += f"/{device_name}"
        entity_topic += f"/{clean_string(entity.name)}"

        state_prefix = settings.mqtt.state_prefix
        logger.debug(f"Using base entity topic: {state_prefix}/{entity_topic}")

        def generate_topic(topic_key: str) -> bool:
            """Generate topic if callback exists"""
            if topic_key in self._callbacks:
                self._topics[topic_key] = f"{state_prefix}/{entity_topic}/{topic_key}"
                return True
            return False

        # Generate command topics based on provided callbacks
        command_topic_keys = [
            MediaPlayerTopics.PLAY,
            MediaPlayerTopics.PAUSE,
            MediaPlayerTopics.STOP,
            MediaPlayerTopics.NEXT_TRACK,
            MediaPlayerTopics.PREVIOUS_TRACK,
            MediaPlayerTopics.VOLUME_SET,
            MediaPlayerTopics.SEEK,
            MediaPlayerTopics.VOLUME_MUTE,
            MediaPlayerTopics.SHUFFLE_SET,
            MediaPlayerTopics.REPEAT_SET,
            MediaPlayerTopics.SELECT_SOURCE,
            MediaPlayerTopics.SELECT_SOUND_MODE,
            MediaPlayerTopics.TURN_ON,
            MediaPlayerTopics.TURN_OFF,
            MediaPlayerTopics.PLAY_MEDIA,
            MediaPlayerTopics.BROWSE_MEDIA,
        ]
        command_topics_generated = sum(int(generate_topic(topic_key)) for topic_key in command_topic_keys)

        logger.debug(f"Generated {command_topics_generated} command topics for callbacks")

        # Generate state topics for properties that might be used
        state_topics_generated = 10  # We always generate 10 state topics
        self._topics[MediaPlayerTopics.STATE] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.STATE}"
        self._topics[MediaPlayerTopics.TITLE] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.TITLE}"
        self._topics[MediaPlayerTopics.ARTIST] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.ARTIST}"
        self._topics[MediaPlayerTopics.ALBUM] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.ALBUM}"
        self._topics[MediaPlayerTopics.DURATION] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.DURATION}"
        self._topics[MediaPlayerTopics.POSITION] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.POSITION}"
        self._topics[MediaPlayerTopics.VOLUME] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.VOLUME}"
        self._topics[MediaPlayerTopics.ALBUMART] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.ALBUMART}"
        self._topics[MediaPlayerTopics.MEDIA_IMAGE_REMOTELY_ACCESSIBLE] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.MEDIA_IMAGE_REMOTELY_ACCESSIBLE}"
        self._topics[MediaPlayerTopics.AVAILABILITY] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.AVAILABILITY}"

        logger.debug(f"Generated {state_topics_generated} state topics (always included)")
        logger.debug(
            f"Total topics generated for MediaPlayer '{entity.name}': {len(self._topics)} "
            f"({command_topics_generated} command + {state_topics_generated} state)"
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
        logger.info(f"Setting {self._entity.name} media image remotely accessible to {message}")
        self._state_helper(message, topic=self._topics["media_image_remotely_accessible"])

    def set_muted(self, muted: bool) -> None:
        """Update mute state"""
        logger.info(f"Setting {self._entity.name} muted to {muted}")
        # Note: mute state typically published to volume topic or separate mute topic
        # For now, we'll use a simple approach

    def set_shuffle(self, shuffle: bool) -> None:
        """Update shuffle state"""
        if MediaPlayerTopics.SHUFFLE_SET not in self._topics:
            raise RuntimeError("Player does not support shuffle control")

        logger.info(f"Setting {self._entity.name} shuffle to {shuffle}")

    def set_repeat(self, repeat: str) -> None:
        """Update repeat mode"""
        if MediaPlayerTopics.REPEAT_SET not in self._topics:
            raise RuntimeError("Player does not support repeat control")

        valid_modes = ["off", "all", "one"]
        if repeat not in valid_modes:
            raise ValueError(f"Invalid repeat mode '{repeat}'. Must be one of: {valid_modes}")

        logger.info(f"Setting {self._entity.name} repeat to {repeat}")

    def set_availability(self, availability: bool) -> None:
        """Update entity availability"""
        message = "online" if availability else "offline"
        logger.info(f"Setting {self._entity.name} availability to {message}")
        self.mqtt_client.publish(self._topics["availability"], message, retain=True)

    # === Bulk Update Methods ===

    def update_media_info(self, title, duration, artist=None, album=None, albumart_url=None, media_image_remotely_accessible=None):
        """Update media properties, clearing all fields first then setting provided values"""
        # Prepare final values - use empty strings/zero for clearing, or provided values
        final_title = title
        final_duration = duration
        final_artist = artist if artist is not None else ""
        final_album = album if album is not None else ""
        final_albumart_url = albumart_url if albumart_url is not None else ""
        final_media_image_remotely_accessible = media_image_remotely_accessible if media_image_remotely_accessible is not None else False

        # Set all values once
        self.set_title(final_title)
        self.set_duration(final_duration)
        self.set_artist(final_artist)
        self.set_album(final_album)
        self.set_albumart_url(final_albumart_url)
        self.set_media_image_remotely_accessible(final_media_image_remotely_accessible)

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
        """Command handler that routes MQTT messages to appropriate callbacks"""
        topic = message.topic
        logger.debug(f"Received MQTT message on topic: {topic}")

        try:
            payload = message.payload.decode()
            logger.debug(f"Decoded payload: {payload}")
        except UnicodeDecodeError:
            logger.exception(f"Failed to decode payload for topic {topic}")
            return

        # Extract command from topic (last part after final slash)
        command_name = topic.split("/")[-1]
        logger.debug(f"Extracted command name: {command_name}")

        # Exit early if no callback registered
        if command_name not in self._callbacks:
            logger.warning(f"No callback registered for command: {command_name}")
            return

        try:
            if command_name in _SIMPLE_COMMANDS:
                logger.debug(f"Invoking simple command callback for: {command_name}")
                self._callbacks[command_name](client, user_data, message)
            else:
                # Payload-based commands need parsing
                parsed_payload = self._parse_command_payload(command_name, payload)
                logger.debug(f"Parsed payload for {command_name}: {parsed_payload}")
                logger.debug(f"Invoking payload-based callback for command: {command_name}")
                self._callbacks[command_name](parsed_payload, client, user_data, message)
            
            logger.debug(f"Successfully executed callback for {command_name}")
        except Exception:
            logger.exception(f"Error executing callback for {command_name}")

    def _parse_command_payload(self, command: str, payload: str):
        """Parse command payload based on command type"""
        import json
        
        logger.debug(f"Parsing payload for command '{command}': {payload}")
        
        match command:
            case MediaPlayerTopics.VOLUME_SET | MediaPlayerTopics.SEEK:
                try:
                    parsed_value = float(payload)
                    logger.debug(f"Parsed float payload for {command}: {parsed_value}")
                    return parsed_value
                except ValueError:
                    logger.exception(f"Invalid float payload for {command}: {payload}")
                    return None
            
            case MediaPlayerTopics.SHUFFLE_SET | MediaPlayerTopics.VOLUME_MUTE:
                parsed_value = payload.upper() == "ON"
                logger.debug(f"Parsed boolean payload for {command}: {parsed_value} (from '{payload}')")
                return parsed_value
            
            case MediaPlayerTopics.REPEAT_SET:
                try:
                    repeat_mode = RepeatMode(payload)
                    logger.debug(f"Parsed repeat mode for {command}: {repeat_mode}")
                    return repeat_mode
                except ValueError:
                    logger.exception(f"Invalid repeat mode for {command}: {payload}. Valid modes: {[mode.value for mode in RepeatMode]}")
                    return None
            
            case MediaPlayerTopics.PLAY_MEDIA:
                try:
                    play_media_payload = PlayMediaPayload.model_validate_json(payload)
                    logger.debug(f"Parsed play_media JSON for {command}: {play_media_payload}")
                    return play_media_payload
                except json.JSONDecodeError:
                    logger.exception(f"Invalid JSON payload for {command}")
                    return None
                except Exception:
                    logger.exception(f"Invalid play_media payload for {command}")
                    return None
            
            case _:
                # String selection commands (select_source, select_sound_mode)
                logger.debug(f"Using string payload for {command}: {payload}")
                return payload

    def generate_config(self) -> dict[str, str]:
        """Generate discovery config based on available topics"""
        logger.debug(f"Generating Home Assistant discovery config for MediaPlayer '{self._entity.name}'")
        config = super().generate_config()

        # Add all available topics to the config
        # HA will determine supported features from topic presence
        topics = {}
        logger.debug(f"Starting with base config keys: {list(config.keys())}")
        logger.debug(f"Processing {len(self._topics)} topics for config generation")

        def add_topic(topic_key: str, config_key: str, category: str) -> bool:
            """Add topic to config if it exists, with debug logging"""
            if topic_key in self._topics:
                topics[config_key] = self._topics[topic_key]
                logger.debug(f"Added {category} topic '{config_key}': {self._topics[topic_key]}")
                return True
            return False

        # Add state topics (always present)
        state_topics_added = 0
        state_topics_added += int(add_topic(MediaPlayerTopics.STATE, "state_topic", "state"))
        if add_topic(MediaPlayerTopics.AVAILABILITY, "availability_topic", "availability"):
            topics["payload_available"] = "online"
            topics["payload_not_available"] = "offline"
            state_topics_added += 1

        # Add metadata topics (always present)
        metadata_topics = [
            (MediaPlayerTopics.TITLE, "media_title_topic"),
            (MediaPlayerTopics.ARTIST, "media_artist_topic"),
            (MediaPlayerTopics.ALBUM, "media_album_name_topic"),
            (MediaPlayerTopics.DURATION, "media_duration_topic"),
            (MediaPlayerTopics.POSITION, "media_position_topic"),
            (MediaPlayerTopics.VOLUME, "volume_level_topic"),
            (MediaPlayerTopics.ALBUMART, "media_image_url_topic"),
            (MediaPlayerTopics.MEDIA_IMAGE_REMOTELY_ACCESSIBLE, "media_image_remotely_accessible_topic"),
        ]
        metadata_topics_added = sum(int(add_topic(topic_key, config_key, "metadata")) for topic_key, config_key in metadata_topics)
        logger.debug(f"Added {metadata_topics_added} metadata topics to config")

        # Add command topics (only present if callbacks provided)
        command_topics = [
            (MediaPlayerTopics.PLAY, "play_topic"),
            (MediaPlayerTopics.PAUSE, "pause_topic"),
            (MediaPlayerTopics.STOP, "stop_topic"),
            (MediaPlayerTopics.NEXT_TRACK, "next_track_topic"),
            (MediaPlayerTopics.PREVIOUS_TRACK, "previous_track_topic"),
            (MediaPlayerTopics.VOLUME_SET, "volume_set_topic"),
            (MediaPlayerTopics.SEEK, "seek_topic"),
            (MediaPlayerTopics.VOLUME_MUTE, "volume_mute_topic"),
            (MediaPlayerTopics.SHUFFLE_SET, "shuffle_set_topic"),
            (MediaPlayerTopics.REPEAT_SET, "repeat_set_topic"),
            (MediaPlayerTopics.SELECT_SOURCE, "select_source_topic"),
            (MediaPlayerTopics.SELECT_SOUND_MODE, "select_sound_mode_topic"),
            (MediaPlayerTopics.TURN_ON, "turn_on_topic"),
            (MediaPlayerTopics.TURN_OFF, "turn_off_topic"),
            (MediaPlayerTopics.PLAY_MEDIA, "play_media_topic"),
            (MediaPlayerTopics.BROWSE_MEDIA, "browse_media_topic"),
        ]
        command_topics_added = sum(int(add_topic(topic_key, config_key, "command")) for topic_key, config_key in command_topics)
        logger.debug(f"Added {command_topics_added} command topics to config")

        final_config = config | topics
        logger.debug(
            f"Generated complete config for MediaPlayer '{self._entity.name}': "
            f"{len(final_config)} total keys ({len(config)} base + {len(topics)} topics)"
        )
        logger.debug(f"Config topic keys: {list(topics.keys())}")
        return final_config
