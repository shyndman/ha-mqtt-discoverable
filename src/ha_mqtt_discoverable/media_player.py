import asyncio
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import ClassVar, Final, TypeAlias, TypedDict, cast, final, override

from aiomqtt import Message
from pydantic import BaseModel, ValidationError

from ha_mqtt_discoverable._base import Discoverable
from ha_mqtt_discoverable._logging import get_logger
from ha_mqtt_discoverable._media_player_manifest import (
    MEDIA_PLAYER_COMMAND_TOPIC_SPECS,
    MEDIA_PLAYER_TOPIC_SPECS,
    MEDIA_PLAYER_TOPIC_SPECS_BY_NAME,
    MediaPlayerCallbackStyle,
    MediaPlayerPayloadParser,
    MediaPlayerTopicSpec,
)
from ha_mqtt_discoverable._models import EntityInfo
from ha_mqtt_discoverable._session import (
    CommandCallback as SessionCommandCallback,
    ParsedCommandCallback as SessionParsedCommandCallback,
    SessionLike,
)
from ha_mqtt_discoverable._topic_paths import build_entity_topic, build_state_topic

logger = get_logger(__name__)

_MAX_LOGGED_URL_LENGTH: Final[int] = 20
_VALID_STATES: Final[frozenset[str]] = frozenset(
    {"playing", "paused", "stopped", "idle", "off"}
)


def _topic_name(name: str) -> str:
    return MEDIA_PLAYER_TOPIC_SPECS_BY_NAME[name].topic


def _truncate_for_log(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value

    return f"{value[: max_chars - 3]}..."


class RepeatMode(str, Enum):
    """Valid repeat modes for media players."""

    OFF = "off"
    ALL = "all"
    ONE = "one"


class PlayMediaPayload(BaseModel):
    """Payload structure for play_media commands."""

    media_type: str
    media_id: str
    enqueue: str | None = None
    announce: bool | None = None


CommandCallback: TypeAlias = Callable[["MediaPlayer", Message], Awaitable[None]]
FloatCallback: TypeAlias = Callable[["MediaPlayer", float, Message], Awaitable[None]]
BoolCallback: TypeAlias = Callable[["MediaPlayer", bool, Message], Awaitable[None]]
SelectionCallback: TypeAlias = Callable[["MediaPlayer", str, Message], Awaitable[None]]
RepeatCallback: TypeAlias = Callable[
    ["MediaPlayer", RepeatMode, Message], Awaitable[None]
]
PlayMediaCallback: TypeAlias = Callable[
    ["MediaPlayer", PlayMediaPayload, Message], Awaitable[None]
]
ParsedCommandPayload: TypeAlias = float | bool | str | RepeatMode | PlayMediaPayload
type CommandPayloadParser = Callable[[Message], ParsedCommandPayload]


@final
class MediaPlayerTopics:
    """Symbolic constants for media player MQTT topic names."""

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

    STATE: ClassVar[str] = _topic_name("state")
    TITLE: ClassVar[str] = _topic_name("title")
    ARTIST: ClassVar[str] = _topic_name("artist")
    ALBUM: ClassVar[str] = _topic_name("album")
    DURATION: ClassVar[str] = _topic_name("duration")
    POSITION: ClassVar[str] = _topic_name("position")
    VOLUME: ClassVar[str] = _topic_name("volume")
    VOLUME_MUTE_STATE: ClassVar[str] = _topic_name("volume_mute_state")
    SHUFFLE_STATE: ClassVar[str] = _topic_name("shuffle_state")
    REPEAT_STATE: ClassVar[str] = _topic_name("repeat_state")
    ALBUMART: ClassVar[str] = _topic_name("albumart")
    MEDIA_IMAGE_REMOTELY_ACCESSIBLE: ClassVar[str] = _topic_name(
        "media_image_remotely_accessible"
    )


class MediaPlayerCallbacks(TypedDict, total=False):
    """Type-safe callback definitions for media player commands."""

    play: CommandCallback
    pause: CommandCallback
    stop: CommandCallback
    next_track: CommandCallback
    previous_track: CommandCallback
    turn_on: CommandCallback
    turn_off: CommandCallback
    browse_media: CommandCallback
    volume_set: FloatCallback
    seek: FloatCallback
    shuffle_set: BoolCallback
    volume_mute: BoolCallback
    repeat_set: RepeatCallback
    select_source: SelectionCallback
    select_sound_mode: SelectionCallback
    play_media: PlayMediaCallback


class MediaPlayerInfo(EntityInfo):
    """Media Player configuration for Home Assistant MQTT discovery."""

    component: str = "media_player"
    volume_step: float | None = 0.1
    source_list: list[str] | None = None
    sound_mode_list: list[str] | None = None
    device_class: str | None = None


class MediaPlayer(Discoverable[MediaPlayerInfo]):
    """Enhanced MQTT media player with property-based state management."""

    _callbacks: MediaPlayerCallbacks
    _topics: dict[str, str]

    def __init__(
        self,
        session: SessionLike,
        entity: MediaPlayerInfo,
        callbacks: MediaPlayerCallbacks,
        *,
        requires_connection: bool = True,
    ) -> None:
        self._callbacks = callbacks.copy()
        self._topics = {}

        super().__init__(
            session,
            entity,
            requires_connection=requires_connection,
        )

        self._generate_topics()
        self._register_command_callbacks()

    def _generate_topics(self) -> None:
        entity_topic = build_entity_topic(self._entity)

        for spec in MEDIA_PLAYER_TOPIC_SPECS:
            required_callback = spec.required_callback or spec.topic
            if not spec.always_include and required_callback not in self._callbacks:
                continue

            self._topics[spec.topic] = build_state_topic(
                self._session.state_prefix,
                entity_topic,
                spec.topic,
            )

    def _register_command_callbacks(self) -> None:
        for spec in MEDIA_PLAYER_COMMAND_TOPIC_SPECS:
            callback = self._callbacks.get(spec.topic)
            if callback is None:
                continue

            parser = self._build_command_parser(spec)
            if parser is None:
                self._session.register_command(
                    self._topics[spec.topic],
                    self,
                    cast(SessionCommandCallback[MediaPlayer], callback),
                    command_name=spec.topic,
                )
                continue

            self._session.register_command(
                self._topics[spec.topic],
                self,
                cast(
                    SessionParsedCommandCallback[MediaPlayer, ParsedCommandPayload],
                    callback,
                ),
                parser=parser,
                command_name=spec.topic,
            )

    def _build_command_parser(
        self,
        spec: MediaPlayerTopicSpec,
    ) -> CommandPayloadParser | None:
        if spec.callback_style is MediaPlayerCallbackStyle.SIMPLE:
            return None

        def parse(message: Message) -> ParsedCommandPayload:
            return self._parse_command_payload(
                spec.topic,
                message.payload.decode("utf-8"),
            )

        return parse

    async def set_state(self, state: str) -> None:
        if state not in _VALID_STATES:
            valid_states = sorted(_VALID_STATES)
            raise ValueError(f"Invalid state '{state}'. Must be one of: {valid_states}")

        logger.info("setting media player state", entity=self._entity.name, state=state)
        await self._state_helper(state, topic=self._topics[MediaPlayerTopics.STATE])

    async def set_title(self, title: str) -> None:
        logger.info("setting media player title", entity=self._entity.name)
        await self._state_helper(title, topic=self._topics[MediaPlayerTopics.TITLE])

    async def set_artist(self, artist: str) -> None:
        logger.info("setting media player artist", entity=self._entity.name)
        await self._state_helper(artist, topic=self._topics[MediaPlayerTopics.ARTIST])

    async def set_album(self, album: str) -> None:
        logger.info("setting media player album", entity=self._entity.name)
        await self._state_helper(album, topic=self._topics[MediaPlayerTopics.ALBUM])

    async def set_volume(self, volume: float) -> None:
        if not 0.0 <= volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {volume}")

        logger.info(
            "setting media player volume",
            entity=self._entity.name,
            volume=volume,
        )
        await self._state_helper(
            str(volume), topic=self._topics[MediaPlayerTopics.VOLUME]
        )

    async def set_position(self, position: int) -> None:
        if position < 0:
            raise ValueError("Position must be non-negative")

        logger.info(
            "setting media player position",
            entity=self._entity.name,
            position=position,
        )
        await self._state_helper(
            str(position),
            topic=self._topics[MediaPlayerTopics.POSITION],
        )

    async def set_duration(self, duration: int) -> None:
        if duration < 0:
            raise ValueError("Duration must be non-negative")

        logger.info(
            "setting media player duration",
            entity=self._entity.name,
            duration=duration,
        )
        await self._state_helper(
            str(duration),
            topic=self._topics[MediaPlayerTopics.DURATION],
        )

    async def set_albumart_url(self, url: str) -> None:
        logger.info(
            "setting media player album art url",
            entity=self._entity.name,
            url=_truncate_for_log(url, _MAX_LOGGED_URL_LENGTH),
        )
        await self._state_helper(url, topic=self._topics[MediaPlayerTopics.ALBUMART])

    async def set_media_image_remotely_accessible(self, accessible: bool) -> None:
        message = "true" if accessible else "false"
        logger.info(
            "setting media image remote accessibility",
            entity=self._entity.name,
            accessible=accessible,
        )
        await self._state_helper(
            message,
            topic=self._topics[MediaPlayerTopics.MEDIA_IMAGE_REMOTELY_ACCESSIBLE],
        )

    async def set_muted(self, muted: bool) -> None:
        if MediaPlayerTopics.VOLUME_MUTE_STATE not in self._topics:
            raise RuntimeError("Player does not support mute state reporting")

        message = "true" if muted else "false"
        logger.info(
            "setting media player mute state",
            entity=self._entity.name,
            muted=muted,
        )
        await self._state_helper(
            message,
            topic=self._topics[MediaPlayerTopics.VOLUME_MUTE_STATE],
        )

    async def set_shuffle(self, shuffle: bool) -> None:
        if MediaPlayerTopics.SHUFFLE_STATE not in self._topics:
            raise RuntimeError("Player does not support shuffle state reporting")

        message = "true" if shuffle else "false"
        logger.info(
            "setting media player shuffle state",
            entity=self._entity.name,
            shuffle=shuffle,
        )
        await self._state_helper(
            message,
            topic=self._topics[MediaPlayerTopics.SHUFFLE_STATE],
        )

    async def set_repeat(self, repeat: str | RepeatMode) -> None:
        if MediaPlayerTopics.REPEAT_STATE not in self._topics:
            raise RuntimeError("Player does not support repeat state reporting")

        repeat_value = repeat.value if isinstance(repeat, RepeatMode) else repeat
        try:
            parsed_repeat = RepeatMode(repeat_value)
        except ValueError as exc:
            valid_modes = [mode.value for mode in RepeatMode]
            raise ValueError(
                f"Invalid repeat mode '{repeat_value}'. Must be one of: {valid_modes}"
            ) from exc

        logger.info(
            "setting media player repeat mode",
            entity=self._entity.name,
            repeat=parsed_repeat.value,
        )
        await self._state_helper(
            parsed_repeat.value,
            topic=self._topics[MediaPlayerTopics.REPEAT_STATE],
        )

    async def update_media_info(
        self,
        title: str,
        duration: int,
        artist: str | None = None,
        album: str | None = None,
        albumart_url: str | None = None,
        media_image_remotely_accessible: bool | None = None,
    ) -> None:
        # Write discovery config once up front; the per-field publishes below
        # are independent, so they are fired concurrently. Without this guard
        # several of them would each lazily trigger write_config and race.
        if not self.wrote_configuration:
            await self.write_config()
        await asyncio.gather(
            self.set_title(title),
            self.set_duration(duration),
            self.set_artist(artist if artist is not None else ""),
            self.set_album(album if album is not None else ""),
            self.set_albumart_url(albumart_url if albumart_url is not None else ""),
            self.set_media_image_remotely_accessible(
                media_image_remotely_accessible
                if media_image_remotely_accessible is not None
                else False
            ),
        )

    async def update_playback_state(
        self,
        state: str | None = None,
        volume: float | None = None,
        muted: bool | None = None,
        shuffle: bool | None = None,
        repeat: str | RepeatMode | None = None,
    ) -> None:
        updates: list[Awaitable[None]] = []
        if state is not None:
            updates.append(self.set_state(state))
        if volume is not None:
            updates.append(self.set_volume(volume))
        if muted is not None:
            updates.append(self.set_muted(muted))
        if shuffle is not None:
            updates.append(self.set_shuffle(shuffle))
        if repeat is not None:
            updates.append(self.set_repeat(repeat))
        if not updates:
            return
        # See update_media_info: write config once before the concurrent batch.
        if not self.wrote_configuration:
            await self.write_config()
        await asyncio.gather(*updates)

    def _parse_command_payload(
        self, command: str, payload: str
    ) -> ParsedCommandPayload:
        spec = MEDIA_PLAYER_TOPIC_SPECS_BY_NAME.get(command)
        if spec is None:
            return payload

        match spec.payload_parser:
            case MediaPlayerPayloadParser.FLOAT:
                try:
                    return float(payload)
                except ValueError as exc:
                    logger.warning(
                        "rejecting media player command with invalid float payload",
                        entity=self._entity.name,
                        command=command,
                        payload=payload,
                    )
                    raise ValueError(f"invalid float payload for {command}") from exc

            case MediaPlayerPayloadParser.BOOL_ON_OFF:
                return payload.upper() == "ON"

            case MediaPlayerPayloadParser.REPEAT_MODE:
                try:
                    return RepeatMode(payload)
                except ValueError as exc:
                    logger.warning(
                        "rejecting media player command with invalid repeat payload",
                        entity=self._entity.name,
                        command=command,
                        payload=payload,
                        valid_values=[mode.value for mode in RepeatMode],
                    )
                    raise ValueError(f"invalid repeat payload for {command}") from exc

            case MediaPlayerPayloadParser.PLAY_MEDIA_JSON:
                try:
                    return PlayMediaPayload.model_validate_json(payload)
                except ValidationError as exc:
                    logger.warning(
                        "rejecting media player command with invalid play media payload",
                        entity=self._entity.name,
                        command=command,
                        payload=_truncate_for_log(payload, _MAX_LOGGED_URL_LENGTH),
                    )
                    raise ValueError(
                        f"invalid play media payload for {command}"
                    ) from exc

            case MediaPlayerPayloadParser.STRING:
                return payload

    @override
    def generate_config(self) -> dict[str, object]:
        config = super().generate_config()
        topic_config: dict[str, object] = {}

        for spec in MEDIA_PLAYER_TOPIC_SPECS:
            topic_url = self._topics.get(spec.topic)
            if topic_url is None:
                continue

            topic_config[spec.config_key] = topic_url

        return config | topic_config
