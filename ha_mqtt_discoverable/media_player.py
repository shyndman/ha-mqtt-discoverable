import logging
from collections.abc import Callable
from typing import TypedDict

from ha_mqtt_discoverable import Discoverable, EntityInfo

logger = logging.getLogger(__name__)


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


class MediaPlayerCallbacks(TypedDict, total=False):
    """Type-safe callback definitions for media player commands"""

    play: Callable[..., None]
    pause: Callable[..., None]
    stop: Callable[..., None]
    next_track: Callable[..., None]
    previous_track: Callable[..., None]
    volume_set: Callable[..., None]
    seek: Callable[..., None]
    volume_mute: Callable[..., None]
    shuffle_set: Callable[..., None]
    repeat_set: Callable[..., None]
    select_source: Callable[..., None]
    select_sound_mode: Callable[..., None]
    turn_on: Callable[..., None]
    turn_off: Callable[..., None]
    play_media: Callable[..., None]
    browse_media: Callable[..., None]


class MediaPlayerInfo(EntityInfo):
    """Enhanced Media Player with property-based state management"""

    component: str = "media_player"

    # === State Properties (represent actual media player state) ===

    # Basic state
    state: str | None = None
    """Current state: playing, paused, stopped, idle, off"""

    # Media information
    media_title: str | None = None
    """Title of current playing media"""

    media_artist: str | None = None
    """Artist of current playing media, music track only"""

    media_album_name: str | None = None
    """Album name of current playing media, music track only"""

    media_album_artist: str | None = None
    """Album artist of current playing media, music track only"""

    media_duration: int | None = None
    """Duration of current playing media in seconds"""

    media_position: int | None = None
    """Position of current playing media in seconds"""

    media_content_id: str | None = None
    """Content ID of current playing media"""

    media_content_type: str | None = None
    """Content type: music, video, podcast, etc."""

    media_track: int | None = None
    """Track number of current playing media, music track only"""

    media_episode: str | None = None
    """Episode of current playing media, TV show only"""

    media_season: str | None = None
    """Season of current playing media, TV show only"""

    media_series_title: str | None = None
    """Title of series of current playing media, TV show only"""

    media_channel: str | None = None
    """Channel currently playing"""

    media_playlist: str | None = None
    """Title of Playlist currently playing"""

    # Audio properties
    volume_level: float | None = None
    """Volume level in range 0.0-1.0"""

    is_volume_muted: bool | None = None
    """True if volume is currently muted"""

    volume_step: float | None = 0.1
    """Volume step for volume_up/volume_down commands"""

    # Playback properties
    shuffle: bool | None = None
    """True if shuffle is enabled"""

    repeat: str | None = None
    """Current repeat mode: off, all, one"""

    # Source/input properties
    source: str | None = None
    """Currently selected input source"""

    source_list: list[str] | None = None
    """List of available input sources"""

    sound_mode: str | None = None
    """Current sound mode"""

    sound_mode_list: list[str] | None = None
    """List of available sound modes"""

    # Media image
    media_image_url: str | None = None
    """Image URL of current playing media"""

    media_image_remotely_accessible: bool | None = False
    """True if media_image_url is accessible outside local network"""

    # App information
    app_id: str | None = None
    """ID of current running app"""

    app_name: str | None = None
    """Name of current running app"""

    # Group properties (for multi-room audio)
    group_members: list[str] | None = None
    """List of player entities currently grouped together"""

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

        # Generate command topics based on provided callbacks
        if MediaPlayerTopics.PLAY in self._callbacks:
            self._topics[MediaPlayerTopics.PLAY] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.PLAY}"
        if MediaPlayerTopics.PAUSE in self._callbacks:
            self._topics[MediaPlayerTopics.PAUSE] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.PAUSE}"
        if MediaPlayerTopics.STOP in self._callbacks:
            self._topics[MediaPlayerTopics.STOP] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.STOP}"
        if MediaPlayerTopics.NEXT_TRACK in self._callbacks:
            self._topics[MediaPlayerTopics.NEXT_TRACK] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.NEXT_TRACK}"
        if MediaPlayerTopics.PREVIOUS_TRACK in self._callbacks:
            self._topics[MediaPlayerTopics.PREVIOUS_TRACK] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.PREVIOUS_TRACK}"
        if MediaPlayerTopics.VOLUME_SET in self._callbacks:
            self._topics[MediaPlayerTopics.VOLUME_SET] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.VOLUME_SET}"
        if MediaPlayerTopics.SEEK in self._callbacks:
            self._topics[MediaPlayerTopics.SEEK] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.SEEK}"
        if MediaPlayerTopics.VOLUME_MUTE in self._callbacks:
            self._topics[MediaPlayerTopics.VOLUME_MUTE] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.VOLUME_MUTE}"
        if MediaPlayerTopics.SHUFFLE_SET in self._callbacks:
            self._topics[MediaPlayerTopics.SHUFFLE_SET] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.SHUFFLE_SET}"
        if MediaPlayerTopics.REPEAT_SET in self._callbacks:
            self._topics[MediaPlayerTopics.REPEAT_SET] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.REPEAT_SET}"
        if MediaPlayerTopics.SELECT_SOURCE in self._callbacks:
            self._topics[MediaPlayerTopics.SELECT_SOURCE] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.SELECT_SOURCE}"
        if MediaPlayerTopics.SELECT_SOUND_MODE in self._callbacks:
            self._topics[MediaPlayerTopics.SELECT_SOUND_MODE] = (
                f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.SELECT_SOUND_MODE}"
            )
        if MediaPlayerTopics.TURN_ON in self._callbacks:
            self._topics[MediaPlayerTopics.TURN_ON] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.TURN_ON}"
        if MediaPlayerTopics.TURN_OFF in self._callbacks:
            self._topics[MediaPlayerTopics.TURN_OFF] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.TURN_OFF}"
        if MediaPlayerTopics.PLAY_MEDIA in self._callbacks:
            self._topics[MediaPlayerTopics.PLAY_MEDIA] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.PLAY_MEDIA}"
        if MediaPlayerTopics.BROWSE_MEDIA in self._callbacks:
            self._topics[MediaPlayerTopics.BROWSE_MEDIA] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.BROWSE_MEDIA}"

        # Generate state topics for properties that might be used
        self._topics[MediaPlayerTopics.STATE] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.STATE}"
        self._topics[MediaPlayerTopics.TITLE] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.TITLE}"
        self._topics[MediaPlayerTopics.ARTIST] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.ARTIST}"
        self._topics[MediaPlayerTopics.ALBUM] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.ALBUM}"
        self._topics[MediaPlayerTopics.DURATION] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.DURATION}"
        self._topics[MediaPlayerTopics.POSITION] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.POSITION}"
        self._topics[MediaPlayerTopics.VOLUME] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.VOLUME}"
        self._topics[MediaPlayerTopics.ALBUMART] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.ALBUMART}"
        self._topics[MediaPlayerTopics.AVAILABILITY] = f"{state_prefix}/{entity_topic}/{MediaPlayerTopics.AVAILABILITY}"

    # === State Update Methods ===

    def set_state(self, state: str) -> None:
        """Update player state with validation"""
        valid_states = ["playing", "paused", "stopped", "idle", "off"]
        if state not in valid_states:
            raise ValueError(f"Invalid state '{state}'. Must be one of: {valid_states}")

        self._entity.state = state
        logger.info(f"Setting {self._entity.name} state to {state}")
        self._state_helper(state, topic=self._topics["state"])

    def set_title(self, title: str) -> None:
        """Update media title"""
        self._entity.media_title = title
        logger.info(f"Setting {self._entity.name} title to {title}")
        self._state_helper(title, topic=self._topics["title"])

    def set_artist(self, artist: str) -> None:
        """Update media artist"""
        self._entity.media_artist = artist
        logger.info(f"Setting {self._entity.name} artist to {artist}")
        self._state_helper(artist, topic=self._topics["artist"])

    def set_album(self, album: str) -> None:
        """Update media album"""
        self._entity.media_album_name = album
        logger.info(f"Setting {self._entity.name} album to {album}")
        self._state_helper(album, topic=self._topics["album"])

    def set_volume(self, volume: float) -> None:
        """Update volume level with validation"""
        if not 0.0 <= volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {volume}")

        self._entity.volume_level = volume
        logger.info(f"Setting {self._entity.name} volume to {volume}")
        self._state_helper(str(volume), topic=self._topics["volume"])

    def set_position(self, position: int) -> None:
        """Update playback position"""
        if position < 0:
            raise ValueError("Position must be non-negative")
        if self._entity.media_duration and position > self._entity.media_duration:
            raise ValueError(f"Position {position} exceeds duration {self._entity.media_duration}")

        self._entity.media_position = position
        logger.info(f"Setting {self._entity.name} position to {position}")
        self._state_helper(str(position), topic=self._topics["position"])

    def set_duration(self, duration: int) -> None:
        """Update media duration"""
        if duration < 0:
            raise ValueError("Duration must be non-negative")

        self._entity.media_duration = duration
        logger.info(f"Setting {self._entity.name} duration to {duration}")
        self._state_helper(str(duration), topic=self._topics["duration"])

    def set_albumart_url(self, url: str) -> None:
        """Update album art URL"""
        self._entity.media_image_url = url
        logger.info(f"Setting {self._entity.name} album art URL to {url}")
        self._state_helper(url, topic=self._topics["albumart"])

    def set_muted(self, muted: bool) -> None:
        """Update mute state"""
        self._entity.is_volume_muted = muted
        logger.info(f"Setting {self._entity.name} muted to {muted}")
        # Note: mute state typically published to volume topic or separate mute topic
        # For now, we'll use a simple approach

    def set_shuffle(self, shuffle: bool) -> None:
        """Update shuffle state"""
        if MediaPlayerTopics.SHUFFLE_SET not in self._topics:
            raise RuntimeError("Player does not support shuffle control")

        self._entity.shuffle = shuffle
        logger.info(f"Setting {self._entity.name} shuffle to {shuffle}")

    def set_repeat(self, repeat: str) -> None:
        """Update repeat mode"""
        if MediaPlayerTopics.REPEAT_SET not in self._topics:
            raise RuntimeError("Player does not support repeat control")

        valid_modes = ["off", "all", "one"]
        if repeat not in valid_modes:
            raise ValueError(f"Invalid repeat mode '{repeat}'. Must be one of: {valid_modes}")

        self._entity.repeat = repeat
        logger.info(f"Setting {self._entity.name} repeat to {repeat}")

    def set_availability(self, available: bool) -> None:
        """Update entity availability"""
        message = "online" if available else "offline"
        logger.info(f"Setting {self._entity.name} availability to {message}")
        self.mqtt_client.publish(self._topics["availability"], message, retain=True)

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
        """Command handler that routes MQTT messages to appropriate callbacks"""
        topic = message.topic

        try:
            payload = message.payload.decode()
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode payload for topic {topic}: {e}")
            return

        # Extract command from topic (last part after final slash)
        command_name = topic.split("/")[-1]

        # Route directly to callback using command name
        if command_name in self._callbacks:
            try:
                parsed_payload = self._parse_command_payload(command_name, payload)
                self._callbacks[command_name](client, user_data, message, parsed_payload)
            except Exception as e:
                logger.error(f"Error executing callback for {command_name}: {e}")
        else:
            logger.warning(f"No callback registered for command: {command_name}")

    def _parse_command_payload(self, command: str, payload: str):
        """Parse command payload based on command type"""
        if command in [MediaPlayerTopics.VOLUME_SET, MediaPlayerTopics.SEEK]:
            try:
                return float(payload)
            except ValueError:
                logger.error(f"Invalid numeric payload for {command}: {payload}")
                return None
        elif command in [MediaPlayerTopics.SHUFFLE_SET, MediaPlayerTopics.VOLUME_MUTE]:
            return payload.upper() == "ON"
        else:
            return payload

    def generate_config(self) -> dict[str, str]:
        """Generate discovery config based on available topics"""
        config = super().generate_config()

        # Add all available topics to the config
        # HA will determine supported features from topic presence
        topics = {}

        # Add state topics (always present)
        if MediaPlayerTopics.STATE in self._topics:
            topics["state_topic"] = self._topics[MediaPlayerTopics.STATE]
        if MediaPlayerTopics.AVAILABILITY in self._topics:
            topics["availability_topic"] = self._topics[MediaPlayerTopics.AVAILABILITY]
            topics["payload_available"] = "online"
            topics["payload_not_available"] = "offline"

        # Add metadata topics (always present)
        if MediaPlayerTopics.TITLE in self._topics:
            topics["media_title_topic"] = self._topics[MediaPlayerTopics.TITLE]
        if MediaPlayerTopics.ARTIST in self._topics:
            topics["media_artist_topic"] = self._topics[MediaPlayerTopics.ARTIST]
        if MediaPlayerTopics.ALBUM in self._topics:
            topics["media_album_name_topic"] = self._topics[MediaPlayerTopics.ALBUM]
        if MediaPlayerTopics.DURATION in self._topics:
            topics["media_duration_topic"] = self._topics[MediaPlayerTopics.DURATION]
        if MediaPlayerTopics.POSITION in self._topics:
            topics["media_position_topic"] = self._topics[MediaPlayerTopics.POSITION]
        if MediaPlayerTopics.VOLUME in self._topics:
            topics["volume_level_topic"] = self._topics[MediaPlayerTopics.VOLUME]
        if MediaPlayerTopics.ALBUMART in self._topics:
            topics["media_image_url_topic"] = self._topics[MediaPlayerTopics.ALBUMART]

        # Add command topics (only present if callbacks provided)
        if MediaPlayerTopics.PLAY in self._topics:
            topics["play_topic"] = self._topics[MediaPlayerTopics.PLAY]
        if MediaPlayerTopics.PAUSE in self._topics:
            topics["pause_topic"] = self._topics[MediaPlayerTopics.PAUSE]
        if MediaPlayerTopics.STOP in self._topics:
            topics["stop_topic"] = self._topics[MediaPlayerTopics.STOP]
        if MediaPlayerTopics.NEXT_TRACK in self._topics:
            topics["next_track_topic"] = self._topics[MediaPlayerTopics.NEXT_TRACK]
        if MediaPlayerTopics.PREVIOUS_TRACK in self._topics:
            topics["previous_track_topic"] = self._topics[MediaPlayerTopics.PREVIOUS_TRACK]
        if MediaPlayerTopics.VOLUME_SET in self._topics:
            topics["volume_set_topic"] = self._topics[MediaPlayerTopics.VOLUME_SET]
        if MediaPlayerTopics.SEEK in self._topics:
            topics["seek_topic"] = self._topics[MediaPlayerTopics.SEEK]
        if MediaPlayerTopics.VOLUME_MUTE in self._topics:
            topics["volume_mute_topic"] = self._topics[MediaPlayerTopics.VOLUME_MUTE]
        if MediaPlayerTopics.SHUFFLE_SET in self._topics:
            topics["shuffle_set_topic"] = self._topics[MediaPlayerTopics.SHUFFLE_SET]
        if MediaPlayerTopics.REPEAT_SET in self._topics:
            topics["repeat_set_topic"] = self._topics[MediaPlayerTopics.REPEAT_SET]
        if MediaPlayerTopics.SELECT_SOURCE in self._topics:
            topics["select_source_topic"] = self._topics[MediaPlayerTopics.SELECT_SOURCE]
        if MediaPlayerTopics.SELECT_SOUND_MODE in self._topics:
            topics["select_sound_mode_topic"] = self._topics[MediaPlayerTopics.SELECT_SOUND_MODE]
        if MediaPlayerTopics.TURN_ON in self._topics:
            topics["turn_on_topic"] = self._topics[MediaPlayerTopics.TURN_ON]
        if MediaPlayerTopics.TURN_OFF in self._topics:
            topics["turn_off_topic"] = self._topics[MediaPlayerTopics.TURN_OFF]
        if MediaPlayerTopics.PLAY_MEDIA in self._topics:
            topics["play_media_topic"] = self._topics[MediaPlayerTopics.PLAY_MEDIA]
        if MediaPlayerTopics.BROWSE_MEDIA in self._topics:
            topics["browse_media_topic"] = self._topics[MediaPlayerTopics.BROWSE_MEDIA]

        return config | topics
