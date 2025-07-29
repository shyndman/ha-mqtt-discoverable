import logging
from typing import Any

from ha_mqtt_discoverable import EntityInfo, Subscriber

logger = logging.getLogger(__name__)

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
            device_name = clean_string(entity.device.name)
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
