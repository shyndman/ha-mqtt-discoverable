import asyncio
import json
from typing import cast

from aiomqtt import Message

from ha_mqtt_discoverable import DeviceInfo, MqttSession, Settings
from ha_mqtt_discoverable.media_player import (
    MediaPlayer,
    MediaPlayerCallbacks,
    MediaPlayerInfo,
    PlayMediaPayload,
    RepeatMode,
)
from ._session_stub import RecordingSession


async def noop_command_callback(_sender: MediaPlayer, _message: Message) -> None:
    return None


async def noop_float_callback(
    _sender: MediaPlayer,
    _value: float,
    _message: Message,
) -> None:
    return None


async def noop_bool_callback(
    _sender: MediaPlayer,
    _value: bool,
    _message: Message,
) -> None:
    return None


async def noop_selection_callback(
    _sender: MediaPlayer,
    _value: str,
    _message: Message,
) -> None:
    return None


async def noop_repeat_callback(
    _sender: MediaPlayer,
    _value: RepeatMode,
    _message: Message,
) -> None:
    return None


async def noop_play_media_callback(
    _sender: MediaPlayer,
    _value: PlayMediaPayload,
    _message: Message,
) -> None:
    return None


def make_player(
    session: RecordingSession,
    *,
    name: str = "test",
    callbacks: MediaPlayerCallbacks | None = None,
    device: DeviceInfo | None = None,
    unique_id: str | None = None,
) -> MediaPlayer:
    return MediaPlayer(
        session,
        MediaPlayerInfo(name=name, device=device, unique_id=unique_id),
        callbacks or {},
    )


def config_string(config: dict[str, object], key: str) -> str:
    value = config[key]
    assert isinstance(value, str)
    return value


def test_minimal_player_omits_optional_topics():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    player = make_player(session)
    config = player.generate_config()

    assert config["component"] == "media_player"
    assert "play_topic" not in config
    assert "volume_mute_command_topic" not in config
    assert "shuffle_set_topic" not in config
    assert "repeat_set_topic" not in config
    assert "volume_mute_state_topic" not in config
    assert "shuffle_state_topic" not in config
    assert "repeat_state_topic" not in config
    assert "media_title_topic" in config
    assert "media_artist_topic" in config
    assert "media_duration_topic" in config


def test_callback_gated_topics_stay_in_lockstep():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    player = make_player(
        session,
        name="partial",
        callbacks={
            "play": noop_command_callback,
            "shuffle_set": noop_bool_callback,
            "repeat_set": noop_repeat_callback,
            "volume_mute": noop_bool_callback,
        },
    )
    config = player.generate_config()

    assert "play_topic" in config
    assert "shuffle_set_topic" in config
    assert "repeat_set_topic" in config
    assert "volume_mute_command_topic" in config
    assert "shuffle_state_topic" in config
    assert "repeat_state_topic" in config
    assert "volume_mute_state_topic" in config
    assert "pause_topic" not in config
    assert "seek_topic" not in config


def test_generate_config_with_device_includes_clean_topic_path():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", state_prefix="ha", client_name="test")
    )
    player = make_player(
        session,
        name="Main Player",
        device=DeviceInfo(name="Living Room TV", identifiers="lr_tv_001"),
        unique_id="lr_main_player",
        callbacks={"play": noop_command_callback},
    )
    config = player.generate_config()

    assert config["unique_id"] == "lr_main_player"
    assert (
        config_string(config, "state_topic")
        == "ha/media_player/living-room-tv/main-player/state"
    )
    assert (
        config_string(config, "play_topic")
        == "ha/media_player/living-room-tv/main-player/play"
    )


def test_state_setters_publish_retained_state():
    session = RecordingSession(
        Settings.MQTT(url="mqtt://localhost", client_name="test")
    )
    player = make_player(
        session,
        callbacks={
            "volume_mute": noop_bool_callback,
            "shuffle_set": noop_bool_callback,
            "repeat_set": noop_repeat_callback,
        },
    )

    async def scenario() -> None:
        await player.set_state("playing")
        await player.set_title("Song Title")
        await player.set_volume(0.4)
        await player.set_muted(True)
        await player.set_shuffle(False)
        await player.set_repeat("all")
        await player.set_available(True)

    asyncio.run(scenario())

    topics = [message.topic for message in session.published]
    assert player.state_topic in topics
    assert all(message.retain is True for message in session.published)


def test_command_routing_uses_sender_first_callback():
    async def scenario() -> None:
        received = asyncio.Event()
        observed: dict[str, str] = {}

        async with MqttSession(
            Settings.MQTT(url="mqtt://localhost", client_name="test")
        ) as session:
            player: MediaPlayer

            async def play_callback(sender: MediaPlayer, message: Message) -> None:
                observed["name"] = cast(str, sender.generate_config()["name"])
                observed["topic"] = str(message.topic)
                observed["payload"] = message.payload.decode()
                received.set()

            player = MediaPlayer(
                session,
                MediaPlayerInfo(name="test_routing"),
                {"play": play_callback},
            )
            topic = config_string(player.generate_config(), "play_topic")
            await session.publish(topic, "PLAY")
            await asyncio.wait_for(received.wait(), timeout=2)

            assert observed == {
                "name": "test_routing",
                "topic": topic,
                "payload": "PLAY",
            }

    asyncio.run(scenario())


def test_volume_set_callback_receives_float_payload():
    observed: dict[str, object] = {}
    received = asyncio.Event()

    async def scenario() -> None:
        async with MqttSession(
            Settings.MQTT(url="mqtt://localhost", client_name="test")
        ) as session:
            player = MediaPlayer(
                session,
                MediaPlayerInfo(name="test_volume"),
                {"volume_set": volume_callback},
            )
            topic = config_string(player.generate_config(), "volume_set_topic")
            await session.publish(topic, "0.75")
            await asyncio.wait_for(received.wait(), timeout=2)

        assert observed == {"name": "test_volume", "value": 0.75}

    async def volume_callback(
        sender: MediaPlayer,
        value: float,
        _message: Message,
    ) -> None:
        observed["name"] = cast(str, sender.generate_config()["name"])
        observed["value"] = value
        received.set()

    asyncio.run(scenario())


def test_shuffle_set_callback_receives_bool_payload():
    async def scenario() -> None:
        received = asyncio.Event()
        observed: list[bool] = []

        async with MqttSession(
            Settings.MQTT(url="mqtt://localhost", client_name="test")
        ) as session:

            async def shuffle_callback(
                _sender: MediaPlayer,
                value: bool,
                _message: Message,
            ) -> None:
                observed.append(value)
                received.set()

            player = MediaPlayer(
                session,
                MediaPlayerInfo(name="test_shuffle"),
                {"shuffle_set": shuffle_callback},
            )
            topic = config_string(player.generate_config(), "shuffle_set_topic")
            await session.publish(topic, "ON")
            await asyncio.wait_for(received.wait(), timeout=2)

        assert observed == [True]

    asyncio.run(scenario())


def test_play_media_callback_receives_parsed_payload():
    async def scenario() -> None:
        received = asyncio.Event()
        observed: dict[str, object] = {}

        async with MqttSession(
            Settings.MQTT(url="mqtt://localhost", client_name="test")
        ) as session:

            async def play_media_callback(
                sender: MediaPlayer,
                value: PlayMediaPayload,
                _message: Message,
            ) -> None:
                observed["name"] = cast(str, sender.generate_config()["name"])
                observed["media_type"] = value.media_type
                observed["media_id"] = value.media_id
                received.set()

            player = MediaPlayer(
                session,
                MediaPlayerInfo(name="test_play_media"),
                {"play_media": play_media_callback},
            )
            topic = config_string(player.generate_config(), "play_media_topic")
            await session.publish(
                topic,
                json.dumps({"media_type": "music", "media_id": "track-123"}),
            )
            await asyncio.wait_for(received.wait(), timeout=2)

        assert observed == {
            "name": "test_play_media",
            "media_type": "music",
            "media_id": "track-123",
        }

    asyncio.run(scenario())


def test_invalid_parsed_payload_does_not_invoke_callback():
    async def scenario() -> None:
        called = asyncio.Event()

        async with MqttSession(
            Settings.MQTT(url="mqtt://localhost", client_name="test")
        ) as session:

            async def volume_callback(
                _sender: MediaPlayer,
                _value: float,
                _message: Message,
            ) -> None:
                called.set()

            player = MediaPlayer(
                session,
                MediaPlayerInfo(name="test_invalid_payload"),
                {"volume_set": volume_callback},
            )
            topic = config_string(player.generate_config(), "volume_set_topic")
            await session.publish(topic, "not-a-number")
            await asyncio.sleep(0.2)

        assert called.is_set() is False

    asyncio.run(scenario())


def test_bool_command_rejects_non_on_off():
    async def scenario() -> None:
        called = asyncio.Event()

        async with MqttSession(
            Settings.MQTT(url="mqtt://localhost", client_name="test")
        ) as session:

            async def shuffle_callback(
                _sender: MediaPlayer,
                _value: bool,
                _message: Message,
            ) -> None:
                called.set()

            player = MediaPlayer(
                session,
                MediaPlayerInfo(name="test_bool_reject"),
                {"shuffle_set": shuffle_callback},
            )
            topic = config_string(player.generate_config(), "shuffle_set_topic")
            await session.publish(topic, "true")
            await asyncio.sleep(0.2)

        assert called.is_set() is False

    asyncio.run(scenario())


def test_bool_command_off_delivers_false():
    async def scenario() -> None:
        received = asyncio.Event()
        observed: list[bool] = []

        async with MqttSession(
            Settings.MQTT(url="mqtt://localhost", client_name="test")
        ) as session:

            async def shuffle_callback(
                _sender: MediaPlayer,
                value: bool,
                _message: Message,
            ) -> None:
                observed.append(value)
                received.set()

            player = MediaPlayer(
                session,
                MediaPlayerInfo(name="test_bool_off"),
                {"shuffle_set": shuffle_callback},
            )
            topic = config_string(player.generate_config(), "shuffle_set_topic")
            await session.publish(topic, "OFF")
            await asyncio.wait_for(received.wait(), timeout=2)

        assert observed == [False]

    asyncio.run(scenario())
