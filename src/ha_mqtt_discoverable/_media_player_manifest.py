from dataclasses import dataclass
from enum import Enum
from typing import Final


class MediaPlayerPayloadParser(str, Enum):
    STRING = "string"
    FLOAT = "float"
    BOOL_ON_OFF = "bool_on_off"
    REPEAT_MODE = "repeat_mode"
    PLAY_MEDIA_JSON = "play_media_json"


class MediaPlayerCallbackStyle(str, Enum):
    SIMPLE = "simple"
    PARSED = "parsed"


@dataclass(frozen=True, slots=True)
class MediaPlayerTopicSpec:
    topic: str
    config_key: str
    always_include: bool
    required_callback: str | None = None
    callback_style: MediaPlayerCallbackStyle | None = None
    payload_parser: MediaPlayerPayloadParser = MediaPlayerPayloadParser.STRING
    adds_availability_payloads: bool = False

    @property
    def is_command(self) -> bool:
        return self.callback_style is not None


MEDIA_PLAYER_TOPIC_SPECS: Final[tuple[MediaPlayerTopicSpec, ...]] = (
    MediaPlayerTopicSpec("state", "state_topic", always_include=True),
    MediaPlayerTopicSpec(
        "availability",
        "availability_topic",
        always_include=True,
        adds_availability_payloads=True,
    ),
    MediaPlayerTopicSpec("title", "media_title_topic", always_include=True),
    MediaPlayerTopicSpec("artist", "media_artist_topic", always_include=True),
    MediaPlayerTopicSpec("album", "media_album_name_topic", always_include=True),
    MediaPlayerTopicSpec("duration", "media_duration_topic", always_include=True),
    MediaPlayerTopicSpec("position", "media_position_topic", always_include=True),
    MediaPlayerTopicSpec("volume", "volume_level_topic", always_include=True),
    MediaPlayerTopicSpec(
        "volume_mute_state",
        "volume_mute_state_topic",
        always_include=False,
        required_callback="volume_mute",
    ),
    MediaPlayerTopicSpec(
        "shuffle_state",
        "shuffle_state_topic",
        always_include=False,
        required_callback="shuffle_set",
    ),
    MediaPlayerTopicSpec(
        "repeat_state",
        "repeat_state_topic",
        always_include=False,
        required_callback="repeat_set",
    ),
    MediaPlayerTopicSpec("albumart", "media_image_url_topic", always_include=True),
    MediaPlayerTopicSpec(
        "media_image_remotely_accessible",
        "media_image_remotely_accessible_topic",
        always_include=True,
    ),
    MediaPlayerTopicSpec(
        "play",
        "play_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.SIMPLE,
    ),
    MediaPlayerTopicSpec(
        "pause",
        "pause_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.SIMPLE,
    ),
    MediaPlayerTopicSpec(
        "stop",
        "stop_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.SIMPLE,
    ),
    MediaPlayerTopicSpec(
        "next_track",
        "next_track_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.SIMPLE,
    ),
    MediaPlayerTopicSpec(
        "previous_track",
        "previous_track_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.SIMPLE,
    ),
    MediaPlayerTopicSpec(
        "volume_set",
        "volume_set_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.PARSED,
        payload_parser=MediaPlayerPayloadParser.FLOAT,
    ),
    MediaPlayerTopicSpec(
        "seek",
        "seek_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.PARSED,
        payload_parser=MediaPlayerPayloadParser.FLOAT,
    ),
    MediaPlayerTopicSpec(
        "volume_mute",
        "volume_mute_command_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.PARSED,
        payload_parser=MediaPlayerPayloadParser.BOOL_ON_OFF,
    ),
    MediaPlayerTopicSpec(
        "shuffle_set",
        "shuffle_set_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.PARSED,
        payload_parser=MediaPlayerPayloadParser.BOOL_ON_OFF,
    ),
    MediaPlayerTopicSpec(
        "repeat_set",
        "repeat_set_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.PARSED,
        payload_parser=MediaPlayerPayloadParser.REPEAT_MODE,
    ),
    MediaPlayerTopicSpec(
        "select_source",
        "select_source_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.PARSED,
    ),
    MediaPlayerTopicSpec(
        "select_sound_mode",
        "select_sound_mode_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.PARSED,
    ),
    MediaPlayerTopicSpec(
        "turn_on",
        "turn_on_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.SIMPLE,
    ),
    MediaPlayerTopicSpec(
        "turn_off",
        "turn_off_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.SIMPLE,
    ),
    MediaPlayerTopicSpec(
        "play_media",
        "play_media_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.PARSED,
        payload_parser=MediaPlayerPayloadParser.PLAY_MEDIA_JSON,
    ),
    MediaPlayerTopicSpec(
        "browse_media",
        "browse_media_topic",
        always_include=False,
        callback_style=MediaPlayerCallbackStyle.SIMPLE,
    ),
)

MEDIA_PLAYER_TOPIC_SPECS_BY_NAME: Final[dict[str, MediaPlayerTopicSpec]] = {
    spec.topic: spec for spec in MEDIA_PLAYER_TOPIC_SPECS
}

MEDIA_PLAYER_COMMAND_TOPIC_SPECS: Final[tuple[MediaPlayerTopicSpec, ...]] = tuple(
    spec for spec in MEDIA_PLAYER_TOPIC_SPECS if spec.is_command
)
