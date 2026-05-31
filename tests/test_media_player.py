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

import time
from collections.abc import Iterator
from threading import Event
from types import SimpleNamespace
from typing import cast

import pytest
from paho.mqtt import publish
from paho.mqtt.client import Client, MQTTMessage
from pydantic import ValidationError

from ha_mqtt_discoverable import DeviceInfo, Settings
from ha_mqtt_discoverable.media_player import (
    MediaPlayer,
    MediaPlayerCallbacks,
    MediaPlayerInfo,
    MediaPlayerTopics,
    ParsedCommandPayload,
    PlayMediaPayload,
    RepeatMode,
)


class MediaPlayerHarness(MediaPlayer):
    def __init__(
        self,
        settings: Settings[MediaPlayerInfo],
        callbacks: MediaPlayerCallbacks,
        user_data: object | None = None,
    ) -> None:
        super().__init__(settings, callbacks, user_data)
        _ACTIVE_PLAYERS.append(self)

    @property
    def topics(self) -> dict[str, str]:
        return self._topics

    @property
    def callbacks(self) -> MediaPlayerCallbacks:
        return self._callbacks

    @property
    def entity(self) -> MediaPlayerInfo:
        return self._entity

    def parse_command_payload(self, command: str, payload: str) -> ParsedCommandPayload:
        return self._parse_command_payload(command, payload)

    def handle_command(
        self,
        client: Client,
        user_data: object,
        message: MQTTMessage,
    ) -> None:
        self._command_callback_handler(client, user_data, message)


_ACTIVE_PLAYERS: list[MediaPlayerHarness] = []


def noop_command_callback(
    _client: Client,
    _user_data: object,
    _message: MQTTMessage,
) -> None:
    return None


def noop_float_callback(
    _value: float,
    _client: Client,
    _user_data: object,
    _message: MQTTMessage,
) -> None:
    return None


def noop_bool_callback(
    _value: bool,
    _client: Client,
    _user_data: object,
    _message: MQTTMessage,
) -> None:
    return None


def noop_selection_callback(
    _value: str,
    _client: Client,
    _user_data: object,
    _message: MQTTMessage,
) -> None:
    return None


def noop_repeat_callback(
    _value: RepeatMode,
    _client: Client,
    _user_data: object,
    _message: MQTTMessage,
) -> None:
    return None


def noop_play_media_callback(
    _value: PlayMediaPayload,
    _client: Client,
    _user_data: object,
    _message: MQTTMessage,
) -> None:
    return None


def make_message(topic: str, payload: str | bytes) -> MQTTMessage:
    return cast(
        MQTTMessage,
        cast(
            object,
            SimpleNamespace(
                topic=topic,
                payload=payload if isinstance(payload, bytes) else payload.encode(),
            ),
        ),
    )


@pytest.fixture
def mqtt_settings() -> Settings.MQTT:
    """Standard MQTT settings for testing"""
    return Settings.MQTT(host="localhost")


@pytest.fixture(autouse=True)
def close_media_players() -> Iterator[None]:
    yield

    while _ACTIVE_PLAYERS:
        _ACTIVE_PLAYERS.pop().close()


@pytest.fixture
def minimal_media_player(mqtt_settings: Settings.MQTT) -> MediaPlayerHarness:
    """MediaPlayer with no callbacks (minimal features)"""
    entity_info = MediaPlayerInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    callbacks: MediaPlayerCallbacks = {}
    return MediaPlayerHarness(settings, callbacks)


@pytest.fixture
def full_featured_media_player(
    mqtt_settings: Settings.MQTT,
) -> MediaPlayerHarness:
    """MediaPlayer with all callbacks (full features)"""
    entity_info = MediaPlayerInfo(name="full_player")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "play": noop_command_callback,
        "pause": noop_command_callback,
        "stop": noop_command_callback,
        "next_track": noop_command_callback,
        "previous_track": noop_command_callback,
        "volume_set": noop_float_callback,
        "seek": noop_float_callback,
        "volume_mute": noop_bool_callback,
        "shuffle_set": noop_bool_callback,
        "repeat_set": noop_repeat_callback,
        "select_source": noop_selection_callback,
        "select_sound_mode": noop_selection_callback,
        "turn_on": noop_command_callback,
        "turn_off": noop_command_callback,
        "play_media": noop_play_media_callback,
        "browse_media": noop_command_callback,
    }
    return MediaPlayerHarness(settings, callbacks)


@pytest.fixture
def partial_media_player(mqtt_settings: Settings.MQTT) -> MediaPlayerHarness:
    """MediaPlayer with some callbacks (partial features)"""
    entity_info = MediaPlayerInfo(name="partial_player")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "play": noop_command_callback,
        "pause": noop_command_callback,
        "volume_set": noop_float_callback,
        "shuffle_set": noop_bool_callback,
    }
    return MediaPlayerHarness(settings, callbacks)


@pytest.fixture
def media_player_with_device(mqtt_settings: Settings.MQTT) -> MediaPlayerHarness:
    """MediaPlayer with device info"""
    device = DeviceInfo(name="test_device", identifiers="test_device_id")
    entity_info = MediaPlayerInfo(
        name="living_room_player", device=device, unique_id="test_living_room"
    )
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "play": noop_command_callback,
        "pause": noop_command_callback,
    }
    return MediaPlayerHarness(settings, callbacks)


# === Constructor and Architecture Tests ===


def test_minimal_media_player_creation(
    minimal_media_player: MediaPlayerHarness,
) -> None:
    """Test creating MediaPlayer with no callbacks"""
    assert minimal_media_player is not None
    assert minimal_media_player.entity.name == "test"
    assert minimal_media_player.callbacks == {}


def test_full_featured_media_player_creation(
    full_featured_media_player: MediaPlayerHarness,
) -> None:
    """Test creating MediaPlayer with all callbacks"""
    assert full_featured_media_player is not None
    assert len(full_featured_media_player.callbacks) == 16

    expected_callbacks = {
        "play",
        "pause",
        "stop",
        "next_track",
        "previous_track",
        "volume_set",
        "seek",
        "volume_mute",
        "shuffle_set",
        "repeat_set",
        "select_source",
        "select_sound_mode",
        "turn_on",
        "turn_off",
        "play_media",
        "browse_media",
    }
    assert set(full_featured_media_player.callbacks.keys()) == expected_callbacks


def test_partial_media_player_creation(
    partial_media_player: MediaPlayerHarness,
) -> None:
    """Test creating MediaPlayer with some callbacks"""
    assert partial_media_player is not None
    assert len(partial_media_player.callbacks) == 4
    assert set(partial_media_player.callbacks.keys()) == {
        "play",
        "pause",
        "volume_set",
        "shuffle_set",
    }


def test_media_player_with_device_creation(
    media_player_with_device: MediaPlayerHarness,
) -> None:
    """Test creating MediaPlayer with device info"""
    assert media_player_with_device is not None
    assert media_player_with_device.entity.device is not None
    assert media_player_with_device.entity.device.name == "test_device"
    assert media_player_with_device.entity.unique_id == "test_living_room"


def test_media_player_device_requires_unique_id() -> None:
    """Test that device info requires unique_id"""
    device = DeviceInfo(name="test_device", identifiers="test_device_id")

    with pytest.raises(
        ValidationError, match="A unique_id is required if a device is defined"
    ):
        _ = MediaPlayerInfo(name="test", device=device)


# === Topic Generation Tests ===


def test_topic_generation_minimal_player(
    minimal_media_player: MediaPlayerHarness,
) -> None:
    """Test topic generation for player with no callbacks"""
    topics = minimal_media_player.topics

    expected_state_topics = {
        MediaPlayerTopics.STATE,
        MediaPlayerTopics.TITLE,
        MediaPlayerTopics.ARTIST,
        MediaPlayerTopics.ALBUM,
        MediaPlayerTopics.DURATION,
        MediaPlayerTopics.POSITION,
        MediaPlayerTopics.VOLUME,
        MediaPlayerTopics.ALBUMART,
        MediaPlayerTopics.MEDIA_IMAGE_REMOTELY_ACCESSIBLE,
        MediaPlayerTopics.AVAILABILITY,
    }
    for topic in expected_state_topics:
        assert topic in topics
        assert "/media_player/test/" in topics[topic]

    command_topics = {
        MediaPlayerTopics.PLAY,
        MediaPlayerTopics.PAUSE,
        MediaPlayerTopics.STOP,
        MediaPlayerTopics.NEXT_TRACK,
        MediaPlayerTopics.PREVIOUS_TRACK,
        MediaPlayerTopics.VOLUME_SET,
        MediaPlayerTopics.SEEK,
    }
    for topic in command_topics:
        assert topic not in topics


def test_topic_generation_full_player(
    full_featured_media_player: MediaPlayerHarness,
) -> None:
    """Test topic generation for player with all callbacks"""
    topics = full_featured_media_player.topics

    expected_all_topics = {
        MediaPlayerTopics.STATE,
        MediaPlayerTopics.TITLE,
        MediaPlayerTopics.ARTIST,
        MediaPlayerTopics.ALBUM,
        MediaPlayerTopics.DURATION,
        MediaPlayerTopics.POSITION,
        MediaPlayerTopics.VOLUME,
        MediaPlayerTopics.ALBUMART,
        MediaPlayerTopics.MEDIA_IMAGE_REMOTELY_ACCESSIBLE,
        MediaPlayerTopics.AVAILABILITY,
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

    for topic in expected_all_topics:
        assert topic in topics
        assert "/media_player/full_player/" in topics[topic]


def test_topic_generation_partial_player(
    partial_media_player: MediaPlayerHarness,
) -> None:
    """Test topic generation for player with some callbacks"""
    topics = partial_media_player.topics

    expected_command_topics = {
        MediaPlayerTopics.PLAY,
        MediaPlayerTopics.PAUSE,
        MediaPlayerTopics.VOLUME_SET,
        MediaPlayerTopics.SHUFFLE_SET,
    }
    unexpected_command_topics = {
        MediaPlayerTopics.STOP,
        MediaPlayerTopics.NEXT_TRACK,
        MediaPlayerTopics.SEEK,
        MediaPlayerTopics.REPEAT_SET,
    }

    for topic in expected_command_topics:
        assert topic in topics

    for topic in unexpected_command_topics:
        assert topic not in topics


def test_topic_generation_with_device(
    media_player_with_device: MediaPlayerHarness,
) -> None:
    """Test topic generation includes device name"""
    topics = media_player_with_device.topics

    for topic_url in topics.values():
        assert "/media_player/test_device/living_room_player/" in topic_url


def test_topic_naming_convention(
    full_featured_media_player: MediaPlayerHarness,
) -> None:
    """Test that topics follow HA-compliant naming convention"""
    topics = full_featured_media_player.topics

    assert MediaPlayerTopics.NEXT_TRACK in topics
    assert MediaPlayerTopics.PREVIOUS_TRACK in topics
    assert MediaPlayerTopics.VOLUME_SET in topics
    assert MediaPlayerTopics.VOLUME_MUTE in topics

    assert topics[MediaPlayerTopics.NEXT_TRACK].endswith("/next_track")
    assert topics[MediaPlayerTopics.PREVIOUS_TRACK].endswith("/previous_track")
    assert topics[MediaPlayerTopics.VOLUME_SET].endswith("/volume_set")
    assert topics[MediaPlayerTopics.VOLUME_MUTE].endswith("/volume_mute")


# === MQTT Subscription Tests (structural validation) ===


def test_minimal_player_has_no_command_topics(
    minimal_media_player: MediaPlayerHarness,
) -> None:
    """Test that minimal player has no command topics to subscribe to"""
    command_topic_keys = [
        MediaPlayerTopics.PLAY,
        MediaPlayerTopics.PAUSE,
        MediaPlayerTopics.STOP,
        MediaPlayerTopics.NEXT_TRACK,
        MediaPlayerTopics.PREVIOUS_TRACK,
        MediaPlayerTopics.VOLUME_SET,
        MediaPlayerTopics.SEEK,
    ]

    for topic_key in command_topic_keys:
        assert topic_key not in minimal_media_player.topics


def test_full_player_has_all_command_topics(
    full_featured_media_player: MediaPlayerHarness,
) -> None:
    """Test that full player has all command topics"""
    expected_command_topics = {
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

    for topic_key in expected_command_topics:
        assert topic_key in full_featured_media_player.topics


def test_partial_player_has_selective_command_topics(
    partial_media_player: MediaPlayerHarness,
) -> None:
    """Test that partial player has only relevant command topics"""
    expected_topics = {
        MediaPlayerTopics.PLAY,
        MediaPlayerTopics.PAUSE,
        MediaPlayerTopics.VOLUME_SET,
        MediaPlayerTopics.SHUFFLE_SET,
    }
    unexpected_topics = {
        MediaPlayerTopics.STOP,
        MediaPlayerTopics.NEXT_TRACK,
        MediaPlayerTopics.SEEK,
        MediaPlayerTopics.REPEAT_SET,
    }

    for topic_key in expected_topics:
        assert topic_key in partial_media_player.topics

    for topic_key in unexpected_topics:
        assert topic_key not in partial_media_player.topics


def test_all_players_have_state_topics():
    """Test that all players have state topics regardless of callbacks"""
    players: list[tuple[str, MediaPlayerCallbacks]] = [
        ("minimal", {}),
        ("partial", {"play": noop_command_callback, "pause": noop_command_callback}),
        (
            "full",
            {
                "play": noop_command_callback,
                "volume_set": noop_float_callback,
                "shuffle_set": noop_bool_callback,
            },
        ),
    ]

    expected_state_topics = {
        MediaPlayerTopics.STATE,
        MediaPlayerTopics.TITLE,
        MediaPlayerTopics.ARTIST,
        MediaPlayerTopics.ALBUM,
        MediaPlayerTopics.DURATION,
        MediaPlayerTopics.POSITION,
        MediaPlayerTopics.VOLUME,
        MediaPlayerTopics.ALBUMART,
        MediaPlayerTopics.MEDIA_IMAGE_REMOTELY_ACCESSIBLE,
        MediaPlayerTopics.AVAILABILITY,
    }

    for player_name, callbacks in players:
        mqtt_settings = Settings.MQTT(host="localhost")
        entity_info = MediaPlayerInfo(name=f"test_state_topics_{player_name}")
        settings = Settings(mqtt=mqtt_settings, entity=entity_info)
        player = MediaPlayerHarness(settings, callbacks)

        for topic_key in expected_state_topics:
            assert topic_key in player.topics, (
                f"{player_name} player missing state topic {topic_key}"
            )


# === Command Routing Tests (with real broker) ===


def test_command_routing_play_command() -> None:
    """Test play command routing through real MQTT broker"""
    # Use real broker for integration testing
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_routing")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    # Track callback invocation
    callback_called = Event()
    received_messages: list[MQTTMessage] = []

    def play_callback(
        _client: Client,
        _user_data: object,
        message: MQTTMessage,
    ) -> None:
        received_messages.append(message)
        callback_called.set()

    callbacks: MediaPlayerCallbacks = {
        "play": play_callback,
    }

    player = MediaPlayerHarness(settings, callbacks)

    # Wait a moment for MQTT connection and subscription
    time.sleep(0.5)

    # Send play command via real broker
    play_topic = player.topics[MediaPlayerTopics.PLAY]
    publish.single(play_topic, "PLAY", hostname="localhost")

    # Wait for callback
    assert callback_called.wait(timeout=2.0), "Play callback was not called"

    # Verify callback received correct arguments
    assert len(received_messages) == 1
    received_message = received_messages[0]
    assert received_message.topic == play_topic
    assert received_message.payload.decode() == "PLAY"


def test_command_routing_volume_set_command() -> None:
    """Test volume_set command routing with numeric payload parsing"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_volume")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callback_called = Event()
    received_payload: float | None = None

    def volume_callback(
        volume: float,
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        nonlocal received_payload
        received_payload = volume
        callback_called.set()

    callbacks: MediaPlayerCallbacks = {
        "volume_set": volume_callback,
    }

    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)

    # Send volume command
    volume_topic = player.topics[MediaPlayerTopics.VOLUME_SET]
    publish.single(volume_topic, "0.75", hostname="localhost")

    assert callback_called.wait(timeout=2.0), "Volume callback was not called"
    assert received_payload == 0.75  # Should be parsed as float


def test_command_routing_shuffle_command() -> None:
    """Test shuffle_set command routing with boolean payload parsing"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_shuffle")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callback_called = Event()
    received_payload: bool | None = None

    def shuffle_callback(
        shuffle: bool,
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        nonlocal received_payload
        received_payload = shuffle
        callback_called.set()

    callbacks: MediaPlayerCallbacks = {
        "shuffle_set": shuffle_callback,
    }

    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)

    # Send shuffle command
    shuffle_topic = player.topics[MediaPlayerTopics.SHUFFLE_SET]
    publish.single(shuffle_topic, "ON", hostname="localhost")

    assert callback_called.wait(timeout=2.0), "Shuffle callback was not called"
    assert received_payload is True  # Should be parsed as boolean


def test_command_routing_no_callback_registered() -> None:
    """Test command routing when no callback is registered"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_no_callback")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    # Create player with play callback but not pause
    callbacks: MediaPlayerCallbacks = {
        "play": noop_command_callback,
    }

    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)

    # Try to send pause command (no callback registered)
    # This should not crash but should log a warning
    # Note: pause topic won't exist because no callback was provided
    assert MediaPlayerTopics.PAUSE not in player.topics


def test_command_routing_multiple_commands() -> None:
    """Test routing multiple different commands to same player"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_multi")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    play_called = Event()
    pause_called = Event()
    volume_called = Event()

    def play_callback(
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        play_called.set()

    def pause_callback(
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        pause_called.set()

    def volume_callback(
        _value: float,
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        volume_called.set()

    callbacks: MediaPlayerCallbacks = {
        "play": play_callback,
        "pause": pause_callback,
        "volume_set": volume_callback,
    }

    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)

    # Send multiple commands
    publish.single(player.topics[MediaPlayerTopics.PLAY], "PLAY", hostname="localhost")
    publish.single(
        player.topics[MediaPlayerTopics.PAUSE], "PAUSE", hostname="localhost"
    )
    publish.single(
        player.topics[MediaPlayerTopics.VOLUME_SET], "0.5", hostname="localhost"
    )

    # All callbacks should be invoked
    assert play_called.wait(timeout=2.0), "Play callback not called"
    assert pause_called.wait(timeout=2.0), "Pause callback not called"
    assert volume_called.wait(timeout=2.0), "Volume callback not called"


# === State Management Tests (with real MQTT) ===


def test_set_state_valid():
    """Test setting valid player states"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_state")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    valid_states = ["playing", "paused", "stopped", "idle", "off"]

    # Should not raise exceptions
    for state in valid_states:
        player.set_state(state)


def test_set_state_invalid():
    """Test setting invalid player state"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_invalid_state")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    with pytest.raises(ValueError, match="Invalid state 'invalid'"):
        player.set_state("invalid")


def test_set_volume_valid():
    """Test setting valid volume levels"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_volume_valid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # Test boundary values
    player.set_volume(0.0)
    player.set_volume(1.0)
    player.set_volume(0.5)


def test_set_volume_invalid():
    """Test setting invalid volume levels"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_volume_invalid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    with pytest.raises(ValueError, match="Volume must be between 0.0 and 1.0"):
        player.set_volume(-0.1)

    with pytest.raises(ValueError, match="Volume must be between 0.0 and 1.0"):
        player.set_volume(1.1)


def test_set_position_valid():
    """Test setting valid playback position"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_position_valid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    player.set_position(0)
    player.set_position(30)
    player.set_position(120)


def test_set_position_invalid():
    """Test setting invalid playback position"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_position_invalid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    with pytest.raises(ValueError, match="Position must be non-negative"):
        player.set_position(-1)


def test_set_duration_valid():
    """Test setting valid media duration"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_duration_valid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    player.set_duration(0)
    player.set_duration(180)
    player.set_duration(3600)


def test_set_duration_invalid():
    """Test setting invalid media duration"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_duration_invalid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    with pytest.raises(ValueError, match="Duration must be non-negative"):
        player.set_duration(-1)


def test_set_media_metadata():
    """Test setting media metadata"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_metadata")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # Should not raise exceptions
    player.set_title("Test Song")
    player.set_artist("Test Artist")
    player.set_album("Test Album")
    player.set_albumart_url("http://example.com/art.jpg")
    player.set_media_image_remotely_accessible(True)
    player.set_media_image_remotely_accessible(False)


def test_set_muted_is_log_only_and_does_not_publish(monkeypatch: pytest.MonkeyPatch):
    """Test that set_muted currently logs only and does not publish state"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_muted")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    publish_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def record_publish(*args: object, **kwargs: object) -> None:
        publish_calls.append((args, kwargs))

    monkeypatch.setattr(player.mqtt_client, "publish", record_publish)

    player.set_muted(True)
    player.set_muted(False)

    assert publish_calls == []


def test_set_shuffle_without_support():
    """Test setting shuffle when not supported"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_shuffle_unsupported")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})  # No shuffle_set callback

    with pytest.raises(RuntimeError, match="Player does not support shuffle control"):
        player.set_shuffle(True)


def test_set_shuffle_with_support_does_not_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that supported shuffle currently validates/logs only"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_shuffle_supported")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "shuffle_set": noop_bool_callback,
    }
    player = MediaPlayerHarness(settings, callbacks)

    publish_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def record_publish(*args: object, **kwargs: object) -> None:
        publish_calls.append((args, kwargs))

    monkeypatch.setattr(player.mqtt_client, "publish", record_publish)

    player.set_shuffle(True)
    player.set_shuffle(False)

    assert publish_calls == []


def test_set_repeat_without_support():
    """Test setting repeat when not supported"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_repeat_unsupported")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})  # No repeat_set callback

    with pytest.raises(RuntimeError, match="Player does not support repeat control"):
        player.set_repeat("all")


def test_set_repeat_with_support_validates_but_does_not_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that supported repeat currently validates/logs only"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_repeat_supported")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "repeat_set": noop_repeat_callback,
    }
    player = MediaPlayerHarness(settings, callbacks)

    publish_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def record_publish(*args: object, **kwargs: object) -> None:
        publish_calls.append((args, kwargs))

    monkeypatch.setattr(player.mqtt_client, "publish", record_publish)

    valid_modes = ["off", "all", "one"]
    for mode in valid_modes:
        player.set_repeat(mode)

    assert publish_calls == []


def test_set_repeat_invalid_mode():
    """Test setting invalid repeat mode"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_repeat_invalid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "repeat_set": noop_repeat_callback,
    }
    player = MediaPlayerHarness(settings, callbacks)

    with pytest.raises(ValueError, match="Invalid repeat mode 'invalid'"):
        player.set_repeat("invalid")


def test_update_media_info():
    """Test bulk media info update"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_bulk_media")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # Should not raise exceptions
    player.update_media_info(
        title="Test Song",
        duration=240,
        artist="Test Artist",
        album="Test Album",
        albumart_url="http://example.com/art.jpg",
        media_image_remotely_accessible=True,
    )


def test_update_media_info_minimal():
    """Test bulk media info update with minimal parameters"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_bulk_minimal")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # Should use defaults for unspecified parameters
    player.update_media_info(title="Minimal Song", duration=180)


def test_update_playback_state():
    """Test bulk playback state update"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_bulk_playback")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "shuffle_set": noop_bool_callback,
        "repeat_set": noop_repeat_callback,
    }
    player = MediaPlayerHarness(settings, callbacks)

    # Should not raise exceptions
    player.update_playback_state(
        state="playing", volume=0.7, muted=False, shuffle=True, repeat="all"
    )


def test_set_availability():
    """Test setting availability"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_availability")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # Should not raise exceptions
    player.set_availability(True)
    player.set_availability(False)


# === Configuration Generation Tests ===


def test_generate_config_minimal_player(
    minimal_media_player: MediaPlayerHarness,
) -> None:
    """Test config generation for minimal player"""
    config = minimal_media_player.generate_config()

    assert config["component"] == "media_player"
    assert config["name"] == "test"
    assert "state_topic" in config
    assert "availability_topic" in config
    assert config["payload_available"] == "online"
    assert config["payload_not_available"] == "offline"

    metadata_topics = [
        "media_title_topic",
        "media_artist_topic",
        "media_album_name_topic",
        "media_duration_topic",
        "media_position_topic",
        "volume_level_topic",
        "media_image_url_topic",
        "media_image_remotely_accessible_topic",
    ]
    for topic in metadata_topics:
        assert topic in config

    command_topics = [
        "play_topic",
        "pause_topic",
        "stop_topic",
        "next_track_topic",
        "previous_track_topic",
        "volume_set_topic",
        "seek_topic",
    ]
    for topic in command_topics:
        assert topic not in config


def test_generate_config_full_player(
    full_featured_media_player: MediaPlayerHarness,
) -> None:
    """Test config generation for full-featured player"""
    config = full_featured_media_player.generate_config()

    expected_command_topics = [
        "play_topic",
        "pause_topic",
        "stop_topic",
        "next_track_topic",
        "previous_track_topic",
        "volume_set_topic",
        "seek_topic",
        "volume_mute_topic",
        "shuffle_set_topic",
        "repeat_set_topic",
        "select_source_topic",
        "select_sound_mode_topic",
        "turn_on_topic",
        "turn_off_topic",
        "play_media_topic",
        "browse_media_topic",
    ]
    for topic in expected_command_topics:
        assert topic in config, f"Missing command topic: {topic}"

    expected_metadata_topics = [
        "media_title_topic",
        "media_artist_topic",
        "media_album_name_topic",
        "media_duration_topic",
        "media_position_topic",
        "volume_level_topic",
        "media_image_url_topic",
        "media_image_remotely_accessible_topic",
    ]
    for topic in expected_metadata_topics:
        assert topic in config, f"Missing metadata topic: {topic}"


def test_generate_config_partial_player(
    partial_media_player: MediaPlayerHarness,
) -> None:
    """Test config generation for partial player"""
    config = partial_media_player.generate_config()

    expected_command_topics = [
        "play_topic",
        "pause_topic",
        "volume_set_topic",
        "shuffle_set_topic",
    ]
    unexpected_command_topics = [
        "stop_topic",
        "next_track_topic",
        "seek_topic",
        "repeat_set_topic",
    ]
    for topic in expected_command_topics:
        assert topic in config, f"Missing expected topic: {topic}"

    for topic in unexpected_command_topics:
        assert topic not in config, f"Unexpected topic present: {topic}"


def test_generate_config_with_device(
    media_player_with_device: MediaPlayerHarness,
) -> None:
    """Test config generation includes device info"""
    config = media_player_with_device.generate_config()

    assert "device" in config
    device_config = config["device"]
    assert isinstance(device_config, dict)
    assert device_config["name"] == "test_device"
    assert device_config["identifiers"] == "test_device_id"
    assert config["unique_id"] == "test_living_room"


def test_generate_config_topic_urls():
    """Test that generated config contains proper topic URLs"""
    mqtt_settings = Settings.MQTT(host="localhost", state_prefix="homeassistant")
    entity_info = MediaPlayerInfo(name="config_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "play": noop_command_callback,
        "volume_set": noop_float_callback,
    }
    player = MediaPlayerHarness(settings, callbacks)

    config = player.generate_config()

    # Verify topic URLs follow expected pattern
    assert config["state_topic"] == "homeassistant/media_player/config_test/state"
    assert config["play_topic"] == "homeassistant/media_player/config_test/play"
    assert (
        config["volume_set_topic"]
        == "homeassistant/media_player/config_test/volume_set"
    )
    assert config["media_title_topic"] == "homeassistant/media_player/config_test/title"


def test_generate_config_with_device_in_topic_path():
    """Test config generation with device affecting topic paths"""
    device = DeviceInfo(name="Living Room TV", identifiers="lr_tv_001")
    mqtt_settings = Settings.MQTT(host="localhost", state_prefix="ha")
    entity_info = MediaPlayerInfo(
        name="Main Player", device=device, unique_id="lr_main_player"
    )
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "play": noop_command_callback,
    }
    player = MediaPlayerHarness(settings, callbacks)

    config = player.generate_config()

    # Topic paths should include cleaned device name (spaces become dashes)
    expected_base = "ha/media_player/living-room-tv/main-player"
    assert config["state_topic"] == f"{expected_base}/state"
    assert config["play_topic"] == f"{expected_base}/play"


def test_config_component_type():
    """Test that component type is always media_player"""
    entity_info = MediaPlayerInfo(name="component_test")
    assert entity_info.component == "media_player"


def test_config_ha_discovery_format():
    """Test that config follows Home Assistant discovery format"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="ha_format_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    callbacks: MediaPlayerCallbacks = {
        "play": noop_command_callback,
        "pause": noop_command_callback,
        "volume_set": noop_float_callback,
    }
    player = MediaPlayerHarness(settings, callbacks)

    config = player.generate_config()

    # Must have these required HA fields
    required_fields = ["name", "state_topic", "availability_topic"]
    for field in required_fields:
        assert field in config, f"Missing required HA field: {field}"

    # Availability payloads must be correct
    assert config["payload_available"] == "online"
    assert config["payload_not_available"] == "offline"


# === End-to-End MQTT Flow Tests ===


def test_complete_media_player_lifecycle():
    """Test complete lifecycle: create → connect → publish state → receive command → cleanup"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="lifecycle_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    # Track command reception
    command_received = Event()
    received_command: dict[str, str] = {}

    def play_handler(
        _client: Client,
        _user_data: object,
        message: MQTTMessage,
    ) -> None:
        received_command["topic"] = message.topic
        received_command["payload"] = message.payload.decode()
        command_received.set()

    callbacks: MediaPlayerCallbacks = {
        "play": play_handler,
        "pause": noop_command_callback,
        "volume_set": noop_float_callback,
    }

    # 1. Create and connect player
    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)  # Allow connection

    # 2. Publish state updates
    player.set_state("playing")
    player.set_title("Test Song")
    player.set_artist("Test Artist")
    player.set_volume(0.8)
    player.set_availability(True)

    # 3. Send command via MQTT
    play_topic = player.topics[MediaPlayerTopics.PLAY]
    publish.single(play_topic, "PLAY", hostname="localhost")

    # 4. Verify command was received and processed
    assert command_received.wait(timeout=2.0), "Play command not received"
    assert received_command["topic"] == play_topic
    assert received_command["payload"] == "PLAY"

    # 5. Verify player state can be updated after command
    player.set_state("paused")
    player.set_position(30)


def test_multiple_players_isolated_commands():
    """Test that multiple players receive only their own commands"""
    mqtt_settings = Settings.MQTT(host="localhost")

    # Create two players with different names
    player1_received = Event()
    player2_received = Event()

    def player1_handler(
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        player1_received.set()

    def player2_handler(
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        player2_received.set()

    # Player 1
    entity_info1 = MediaPlayerInfo(name="isolated_test_1")
    settings1 = Settings(mqtt=mqtt_settings, entity=entity_info1)
    callbacks1: MediaPlayerCallbacks = {"play": player1_handler}
    player1 = MediaPlayerHarness(settings1, callbacks1)

    # Player 2
    entity_info2 = MediaPlayerInfo(name="isolated_test_2")
    settings2 = Settings(mqtt=mqtt_settings, entity=entity_info2)
    callbacks2: MediaPlayerCallbacks = {"play": player2_handler}
    player2 = MediaPlayerHarness(settings2, callbacks2)

    time.sleep(0.5)  # Allow connections

    # Send command only to player1
    play_topic1 = player1.topics[MediaPlayerTopics.PLAY]
    play_topic2 = player2.topics[MediaPlayerTopics.PLAY]
    assert play_topic1 != play_topic2
    publish.single(play_topic1, "PLAY", hostname="localhost")

    # Only player1 should receive the command
    assert player1_received.wait(timeout=2.0), "Player1 did not receive its command"
    assert not player2_received.is_set(), (
        "Player2 incorrectly received player1's command"
    )


def test_player_with_device_end_to_end():
    """Test end-to-end flow for player with device info"""
    device = DeviceInfo(name="Test Device", identifiers="test_device_123")
    mqtt_settings = Settings.MQTT(host="localhost", state_prefix="test")
    entity_info = MediaPlayerInfo(
        name="Device Player", device=device, unique_id="device_player_001"
    )
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    volume_command_received = Event()
    received_volume: float | None = None

    def volume_handler(
        volume: float,
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        nonlocal received_volume
        received_volume = volume
        volume_command_received.set()

    callbacks: MediaPlayerCallbacks = {
        "volume_set": volume_handler,
    }

    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)

    # Verify device info in config
    config = player.generate_config()
    device_config = config["device"]
    assert isinstance(device_config, dict)
    assert device_config["name"] == "Test Device"
    assert config["unique_id"] == "device_player_001"

    # Test command with device-specific topic path (spaces become dashes)
    volume_topic = player.topics[MediaPlayerTopics.VOLUME_SET]
    assert "/test-device/device-player/" in volume_topic

    # Send volume command
    publish.single(volume_topic, "0.65", hostname="localhost")

    assert volume_command_received.wait(timeout=2.0), "Volume command not received"
    assert received_volume == 0.65  # Parsed as float


def test_error_handling_in_command_flow():
    """Test callback errors surface from the command handler"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="error_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    # Create callback that raises an exception
    def error_callback(
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        raise ValueError("Test error in callback")

    callbacks: MediaPlayerCallbacks = {
        "play": error_callback,
    }

    player = MediaPlayerHarness(settings, callbacks)
    message = make_message(player.topics[MediaPlayerTopics.PLAY], "PLAY")

    with pytest.raises(ValueError, match="Test error in callback"):
        player.handle_command(player.mqtt_client, object(), message)


def test_rapid_command_sequence():
    """Test handling of rapid command sequence"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="rapid_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    commands_received: list[str | float] = []
    commands_lock = Event()

    # Different handlers for different command types
    def play_command_handler(
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        commands_received.append("PLAY")
        if len(commands_received) >= 3:
            commands_lock.set()

    def pause_command_handler(
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        commands_received.append("PAUSE")
        if len(commands_received) >= 3:
            commands_lock.set()

    def volume_command_handler(
        volume: float,
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        commands_received.append(volume)
        if len(commands_received) >= 3:
            commands_lock.set()

    callbacks: MediaPlayerCallbacks = {
        "play": play_command_handler,
        "pause": pause_command_handler,
        "volume_set": volume_command_handler,
    }

    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)

    # Send rapid sequence of commands
    publish.single(player.topics[MediaPlayerTopics.PLAY], "PLAY", hostname="localhost")
    publish.single(
        player.topics[MediaPlayerTopics.PAUSE], "PAUSE", hostname="localhost"
    )
    publish.single(
        player.topics[MediaPlayerTopics.VOLUME_SET], "0.7", hostname="localhost"
    )

    # All commands should be processed
    assert commands_lock.wait(timeout=3.0), "Not all rapid commands were processed"
    assert len(commands_received) == 3
    assert "PLAY" in commands_received
    assert "PAUSE" in commands_received
    assert 0.7 in commands_received  # Volume parsed as float


# === Payload Parsing Validation Tests ===


def test_parse_command_payload_numeric_commands():
    """Test payload parsing for numeric commands"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_numeric_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # Volume set commands should parse as float
    assert player.parse_command_payload(MediaPlayerTopics.VOLUME_SET, "0.5") == 0.5
    assert player.parse_command_payload(MediaPlayerTopics.VOLUME_SET, "1.0") == 1.0
    assert player.parse_command_payload(MediaPlayerTopics.VOLUME_SET, "0") == 0.0

    # Seek commands should parse as float
    assert player.parse_command_payload(MediaPlayerTopics.SEEK, "30") == 30.0
    assert player.parse_command_payload(MediaPlayerTopics.SEEK, "120.5") == 120.5


def test_parse_command_payload_boolean_commands():
    """Test payload parsing for boolean commands"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_boolean_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # Shuffle commands
    assert player.parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "ON") is True
    assert player.parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "OFF") is False
    assert player.parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "on") is True
    assert player.parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "off") is False

    # Volume mute commands
    assert player.parse_command_payload(MediaPlayerTopics.VOLUME_MUTE, "ON") is True
    assert player.parse_command_payload(MediaPlayerTopics.VOLUME_MUTE, "OFF") is False


def test_parse_command_payload_string_commands():
    """Test payload parsing for string commands"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_string_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # String commands should return raw payload
    assert player.parse_command_payload(MediaPlayerTopics.PLAY, "PLAY") == "PLAY"
    assert player.parse_command_payload(MediaPlayerTopics.PAUSE, "PAUSE") == "PAUSE"
    assert (
        player.parse_command_payload(MediaPlayerTopics.SELECT_SOURCE, "CD Player")
        == "CD Player"
    )
    assert (
        player.parse_command_payload(MediaPlayerTopics.SELECT_SOURCE, "Bluetooth")
        == "Bluetooth"
    )
    assert (
        player.parse_command_payload(MediaPlayerTopics.SELECT_SOUND_MODE, "Movie")
        == "Movie"
    )


def test_parse_command_payload_invalid_numeric():
    """Test payload parsing with invalid numeric values"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_invalid_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # Invalid numeric payloads should return None
    assert player.parse_command_payload(MediaPlayerTopics.VOLUME_SET, "invalid") is None
    assert player.parse_command_payload(MediaPlayerTopics.VOLUME_SET, "abc") is None
    assert player.parse_command_payload(MediaPlayerTopics.SEEK, "not_a_number") is None


def test_parse_command_payload_edge_cases():
    """Test payload parsing edge cases"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_edge_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    # Empty strings
    assert player.parse_command_payload(MediaPlayerTopics.PLAY, "") == ""
    assert (
        player.parse_command_payload(MediaPlayerTopics.VOLUME_SET, "") is None
    )  # Invalid float

    # Whitespace
    assert (
        player.parse_command_payload(MediaPlayerTopics.SELECT_SOURCE, "  Spotify  ")
        == "  Spotify  "
    )

    # Boolean edge cases
    assert (
        player.parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "True") is False
    )  # Only "ON" is True
    assert (
        player.parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "1") is False
    )  # Only "ON" is True


def test_parse_command_payload_play_media_expected_failures_return_none():
    """Test play_media parsing returns None for invalid JSON or invalid payloads"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_play_media_invalid_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    assert player.parse_command_payload(MediaPlayerTopics.PLAY_MEDIA, "{") is None
    assert (
        player.parse_command_payload(
            MediaPlayerTopics.PLAY_MEDIA,
            '{"media_type": "music"}',
        )
        is None
    )


def test_parse_command_payload_play_media_unexpected_error_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test play_media parsing re-raises unexpected parser failures"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_play_media_error_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayerHarness(settings, {})

    def raise_unexpected(_payload: str) -> PlayMediaPayload:
        raise RuntimeError("unexpected parser failure")

    monkeypatch.setattr(PlayMediaPayload, "model_validate_json", raise_unexpected)

    with pytest.raises(RuntimeError, match="unexpected parser failure"):
        player.parse_command_payload(
            MediaPlayerTopics.PLAY_MEDIA,
            '{"media_type": "music", "media_id": "123"}',
        )


def test_payload_parsing_integration_volume():
    """Integration test: volume command with parsed payload"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="integration_volume_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    received_payload: float | None = None
    callback_called = Event()

    def volume_callback(
        volume: float,
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        nonlocal received_payload
        received_payload = volume
        callback_called.set()

    callbacks: MediaPlayerCallbacks = {
        "volume_set": volume_callback,
    }

    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)

    # Send string volume, should be parsed to float
    volume_topic = player.topics[MediaPlayerTopics.VOLUME_SET]
    publish.single(volume_topic, "0.85", hostname="localhost")

    assert callback_called.wait(timeout=2.0), "Volume callback not called"
    assert received_payload == 0.85
    assert isinstance(received_payload, float)


def test_payload_parsing_integration_boolean():
    """Integration test: shuffle command with parsed payload"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="integration_boolean_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    received_payload: bool | None = None
    callback_called = Event()

    def shuffle_callback(
        shuffle: bool,
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        nonlocal received_payload
        received_payload = shuffle
        callback_called.set()

    callbacks: MediaPlayerCallbacks = {
        "shuffle_set": shuffle_callback,
    }

    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)

    # Send string "OFF", should be parsed to False
    shuffle_topic = player.topics[MediaPlayerTopics.SHUFFLE_SET]
    publish.single(shuffle_topic, "OFF", hostname="localhost")

    assert callback_called.wait(timeout=2.0), "Shuffle callback not called"
    assert received_payload is False


def test_payload_parsing_integration_string():
    """Integration test: string command with raw payload"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="integration_string_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)

    received_payload: str | None = None
    callback_called = Event()

    def source_callback(
        source: str,
        _client: Client,
        _user_data: object,
        _message: MQTTMessage,
    ) -> None:
        nonlocal received_payload
        received_payload = source
        callback_called.set()

    callbacks: MediaPlayerCallbacks = {
        "select_source": source_callback,
    }

    player = MediaPlayerHarness(settings, callbacks)
    time.sleep(0.5)

    # Send string source, should remain as string
    source_topic = player.topics[MediaPlayerTopics.SELECT_SOURCE]
    publish.single(source_topic, "Aux Input", hostname="localhost")

    assert callback_called.wait(timeout=2.0), "Source callback not called"
    assert received_payload == "Aux Input"
