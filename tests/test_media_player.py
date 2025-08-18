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
from threading import Event
from unittest.mock import MagicMock, patch

import pytest
from paho.mqtt import publish
from pydantic import ValidationError

from ha_mqtt_discoverable import DeviceInfo, Settings
from ha_mqtt_discoverable.media_player import (
    MediaPlayer,
    MediaPlayerCallbacks,
    MediaPlayerInfo,
    MediaPlayerTopics,
)


@pytest.fixture
def mqtt_settings():
    """Standard MQTT settings for testing"""
    return Settings.MQTT(host="localhost")


@pytest.fixture
def minimal_media_player(mqtt_settings):
    """MediaPlayer with no callbacks (minimal features)"""
    entity_info = MediaPlayerInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    callbacks: MediaPlayerCallbacks = {}
    return MediaPlayer(settings, callbacks)


@pytest.fixture  
def full_featured_media_player(mqtt_settings):
    """MediaPlayer with all callbacks (full features)"""
    entity_info = MediaPlayerInfo(name="full_player")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    # Create mock callbacks for all supported commands
    callbacks: MediaPlayerCallbacks = {
        'play': MagicMock(),
        'pause': MagicMock(),
        'stop': MagicMock(),
        'next_track': MagicMock(),
        'previous_track': MagicMock(),
        'volume_set': MagicMock(),
        'seek': MagicMock(),
        'volume_mute': MagicMock(),
        'shuffle_set': MagicMock(),
        'repeat_set': MagicMock(),
        'select_source': MagicMock(),
        'select_sound_mode': MagicMock(),
        'turn_on': MagicMock(),
        'turn_off': MagicMock(),
        'play_media': MagicMock(),
        'browse_media': MagicMock(),
    }
    return MediaPlayer(settings, callbacks)


@pytest.fixture
def partial_media_player(mqtt_settings):
    """MediaPlayer with some callbacks (partial features)"""
    entity_info = MediaPlayerInfo(name="partial_player")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callbacks: MediaPlayerCallbacks = {
        'play': MagicMock(),
        'pause': MagicMock(), 
        'volume_set': MagicMock(),
        'shuffle_set': MagicMock(),
    }
    return MediaPlayer(settings, callbacks)


@pytest.fixture
def media_player_with_device(mqtt_settings):
    """MediaPlayer with device info"""
    device = DeviceInfo(name="test_device", identifiers="test_device_id")
    entity_info = MediaPlayerInfo(name="living_room_player", device=device, unique_id="test_living_room")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callbacks: MediaPlayerCallbacks = {
        'play': MagicMock(),
        'pause': MagicMock(),
    }
    return MediaPlayer(settings, callbacks)


# === Constructor and Architecture Tests ===


def test_minimal_media_player_creation(minimal_media_player):
    """Test creating MediaPlayer with no callbacks"""
    assert minimal_media_player is not None
    assert minimal_media_player._entity.name == "test"
    assert minimal_media_player._callbacks == {}


def test_full_featured_media_player_creation(full_featured_media_player):
    """Test creating MediaPlayer with all callbacks"""
    assert full_featured_media_player is not None
    assert len(full_featured_media_player._callbacks) == 16
    
    # Verify all expected callbacks are present
    expected_callbacks = {
        'play', 'pause', 'stop', 'next_track', 'previous_track', 'volume_set',
        'seek', 'volume_mute', 'shuffle_set', 'repeat_set', 'select_source', 
        'select_sound_mode', 'turn_on', 'turn_off', 'play_media', 'browse_media'
    }
    assert set(full_featured_media_player._callbacks.keys()) == expected_callbacks


def test_partial_media_player_creation(partial_media_player):
    """Test creating MediaPlayer with some callbacks"""
    assert partial_media_player is not None
    assert len(partial_media_player._callbacks) == 4
    assert set(partial_media_player._callbacks.keys()) == {'play', 'pause', 'volume_set', 'shuffle_set'}


def test_media_player_with_device_creation(media_player_with_device):
    """Test creating MediaPlayer with device info"""
    assert media_player_with_device is not None
    assert media_player_with_device._entity.device.name == "test_device"
    assert media_player_with_device._entity.unique_id == "test_living_room"


def test_media_player_device_requires_unique_id(mqtt_settings):
    """Test that device info requires unique_id"""
    device = DeviceInfo(name="test_device", identifiers="test_device_id")
    
    # Pydantic validates this at MediaPlayerInfo creation, not MediaPlayer creation
    with pytest.raises(ValidationError, match="A unique_id is required if a device is defined"):
        MediaPlayerInfo(name="test", device=device)  # No unique_id


# === Topic Generation Tests ===


def test_topic_generation_minimal_player(minimal_media_player):
    """Test topic generation for player with no callbacks"""
    topics = minimal_media_player._topics
    
    # Should have all state topics but no command topics
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
    
    # Verify state topics exist
    for topic in expected_state_topics:
        assert topic in topics
        assert "/media_player/test/" in topics[topic]
    
    # Verify no command topics exist
    command_topics = {
        MediaPlayerTopics.PLAY, MediaPlayerTopics.PAUSE, MediaPlayerTopics.STOP,
        MediaPlayerTopics.NEXT_TRACK, MediaPlayerTopics.PREVIOUS_TRACK,
        MediaPlayerTopics.VOLUME_SET, MediaPlayerTopics.SEEK,
    }
    for topic in command_topics:
        assert topic not in topics


def test_topic_generation_full_player(full_featured_media_player):
    """Test topic generation for player with all callbacks"""
    topics = full_featured_media_player._topics
    
    # Should have both state and command topics
    expected_all_topics = {
        # State topics
        MediaPlayerTopics.STATE, MediaPlayerTopics.TITLE, MediaPlayerTopics.ARTIST,
        MediaPlayerTopics.ALBUM, MediaPlayerTopics.DURATION, MediaPlayerTopics.POSITION,
        MediaPlayerTopics.VOLUME, MediaPlayerTopics.ALBUMART, 
        MediaPlayerTopics.MEDIA_IMAGE_REMOTELY_ACCESSIBLE, MediaPlayerTopics.AVAILABILITY,
        # Command topics
        MediaPlayerTopics.PLAY, MediaPlayerTopics.PAUSE, MediaPlayerTopics.STOP,
        MediaPlayerTopics.NEXT_TRACK, MediaPlayerTopics.PREVIOUS_TRACK,
        MediaPlayerTopics.VOLUME_SET, MediaPlayerTopics.SEEK, MediaPlayerTopics.VOLUME_MUTE,
        MediaPlayerTopics.SHUFFLE_SET, MediaPlayerTopics.REPEAT_SET,
        MediaPlayerTopics.SELECT_SOURCE, MediaPlayerTopics.SELECT_SOUND_MODE,
        MediaPlayerTopics.TURN_ON, MediaPlayerTopics.TURN_OFF,
        MediaPlayerTopics.PLAY_MEDIA, MediaPlayerTopics.BROWSE_MEDIA,
    }
    
    for topic in expected_all_topics:
        assert topic in topics
        assert "/media_player/full_player/" in topics[topic]


def test_topic_generation_partial_player(partial_media_player):
    """Test topic generation for player with some callbacks"""
    topics = partial_media_player._topics
    
    # Should have state topics plus specific command topics
    expected_command_topics = {
        MediaPlayerTopics.PLAY, MediaPlayerTopics.PAUSE, 
        MediaPlayerTopics.VOLUME_SET, MediaPlayerTopics.SHUFFLE_SET
    }
    unexpected_command_topics = {
        MediaPlayerTopics.STOP, MediaPlayerTopics.NEXT_TRACK,
        MediaPlayerTopics.SEEK, MediaPlayerTopics.REPEAT_SET
    }
    
    # Verify expected command topics exist
    for topic in expected_command_topics:
        assert topic in topics
        
    # Verify unexpected command topics don't exist  
    for topic in unexpected_command_topics:
        assert topic not in topics


def test_topic_generation_with_device(media_player_with_device):
    """Test topic generation includes device name"""
    topics = media_player_with_device._topics
    
    # Topics should include device name in path
    for topic_url in topics.values():
        assert "/media_player/test_device/living_room_player/" in topic_url


def test_topic_naming_convention(full_featured_media_player):
    """Test that topics follow HA-compliant naming convention"""
    topics = full_featured_media_player._topics
    
    # Verify specific HA-compliant topic names
    assert MediaPlayerTopics.NEXT_TRACK in topics  # Not just "next"
    assert MediaPlayerTopics.PREVIOUS_TRACK in topics  # Not just "previous" 
    assert MediaPlayerTopics.VOLUME_SET in topics  # Not just "volumeset"
    assert MediaPlayerTopics.VOLUME_MUTE in topics  # Not just "mute"
    
    # Verify topics end with the correct suffix
    assert topics[MediaPlayerTopics.NEXT_TRACK].endswith("/next_track")
    assert topics[MediaPlayerTopics.PREVIOUS_TRACK].endswith("/previous_track")
    assert topics[MediaPlayerTopics.VOLUME_SET].endswith("/volume_set")
    assert topics[MediaPlayerTopics.VOLUME_MUTE].endswith("/volume_mute")


# === MQTT Subscription Tests (structural validation) ===


def test_minimal_player_has_no_command_topics(minimal_media_player):
    """Test that minimal player has no command topics to subscribe to"""
    # Command topics should not exist without callbacks
    command_topic_keys = [
        MediaPlayerTopics.PLAY, MediaPlayerTopics.PAUSE, MediaPlayerTopics.STOP,
        MediaPlayerTopics.NEXT_TRACK, MediaPlayerTopics.PREVIOUS_TRACK,
        MediaPlayerTopics.VOLUME_SET, MediaPlayerTopics.SEEK,
    ]
    
    for topic_key in command_topic_keys:
        assert topic_key not in minimal_media_player._topics


def test_full_player_has_all_command_topics(full_featured_media_player):
    """Test that full player has all command topics"""
    expected_command_topics = {
        MediaPlayerTopics.PLAY, MediaPlayerTopics.PAUSE, MediaPlayerTopics.STOP,
        MediaPlayerTopics.NEXT_TRACK, MediaPlayerTopics.PREVIOUS_TRACK,
        MediaPlayerTopics.VOLUME_SET, MediaPlayerTopics.SEEK, MediaPlayerTopics.VOLUME_MUTE,
        MediaPlayerTopics.SHUFFLE_SET, MediaPlayerTopics.REPEAT_SET,
        MediaPlayerTopics.SELECT_SOURCE, MediaPlayerTopics.SELECT_SOUND_MODE,
        MediaPlayerTopics.TURN_ON, MediaPlayerTopics.TURN_OFF,
        MediaPlayerTopics.PLAY_MEDIA, MediaPlayerTopics.BROWSE_MEDIA,
    }
    
    for topic_key in expected_command_topics:
        assert topic_key in full_featured_media_player._topics


def test_partial_player_has_selective_command_topics(partial_media_player):
    """Test that partial player has only relevant command topics"""
    expected_topics = {
        MediaPlayerTopics.PLAY, MediaPlayerTopics.PAUSE,
        MediaPlayerTopics.VOLUME_SET, MediaPlayerTopics.SHUFFLE_SET
    }
    unexpected_topics = {
        MediaPlayerTopics.STOP, MediaPlayerTopics.NEXT_TRACK,
        MediaPlayerTopics.SEEK, MediaPlayerTopics.REPEAT_SET
    }
    
    for topic_key in expected_topics:
        assert topic_key in partial_media_player._topics
        
    for topic_key in unexpected_topics:
        assert topic_key not in partial_media_player._topics


def test_all_players_have_state_topics():
    """Test that all players have state topics regardless of callbacks"""
    players = [
        ('minimal', {}),
        ('partial', {'play': MagicMock(), 'pause': MagicMock()}),
        ('full', {'play': MagicMock(), 'volume_set': MagicMock(), 'shuffle_set': MagicMock()})
    ]
    
    expected_state_topics = {
        MediaPlayerTopics.STATE, MediaPlayerTopics.TITLE, MediaPlayerTopics.ARTIST,
        MediaPlayerTopics.ALBUM, MediaPlayerTopics.DURATION, MediaPlayerTopics.POSITION,
        MediaPlayerTopics.VOLUME, MediaPlayerTopics.ALBUMART,
        MediaPlayerTopics.MEDIA_IMAGE_REMOTELY_ACCESSIBLE, MediaPlayerTopics.AVAILABILITY,
    }
    
    for player_name, callbacks in players:
        mqtt_settings = Settings.MQTT(host="localhost")
        entity_info = MediaPlayerInfo(name=f"test_state_topics_{player_name}")
        settings = Settings(mqtt=mqtt_settings, entity=entity_info)
        player = MediaPlayer(settings, callbacks)
        
        for topic_key in expected_state_topics:
            assert topic_key in player._topics, f"{player_name} player missing state topic {topic_key}"


# === Command Routing Tests (with real broker) ===


def test_command_routing_play_command():
    """Test play command routing through real MQTT broker"""
    # Use real broker for integration testing
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_routing")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    # Track callback invocation
    callback_called = Event()
    received_args = {}
    
    def play_callback(client, user_data, message):
        received_args['client'] = client
        received_args['user_data'] = user_data  
        received_args['message'] = message
        # For simple commands, we don't expect a parsed payload
        received_args['parsed_payload'] = message.payload.decode()
        callback_called.set()
    
    callbacks: MediaPlayerCallbacks = {
        'play': play_callback,
    }
    
    player = MediaPlayer(settings, callbacks)
    
    # Wait a moment for MQTT connection and subscription
    time.sleep(0.5)
    
    # Send play command via real broker
    play_topic = player._topics[MediaPlayerTopics.PLAY]
    publish.single(play_topic, "PLAY", hostname="localhost")
    
    # Wait for callback
    assert callback_called.wait(timeout=2.0), "Play callback was not called"
    
    # Verify callback received correct arguments
    assert received_args['client'] is not None
    assert received_args['message'].topic == play_topic
    assert received_args['message'].payload.decode() == "PLAY"
    assert received_args['parsed_payload'] == "PLAY"


def test_command_routing_volume_set_command():
    """Test volume_set command routing with numeric payload parsing"""
    mqtt_settings = Settings.MQTT(host="localhost") 
    entity_info = MediaPlayerInfo(name="test_volume")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callback_called = Event()
    received_payload = None
    
    def volume_callback(volume: float, client, user_data, message):
        nonlocal received_payload
        # Volume is now passed as first parameter, already parsed
        received_payload = volume
        callback_called.set()
    
    callbacks: MediaPlayerCallbacks = {
        'volume_set': volume_callback,
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Send volume command
    volume_topic = player._topics[MediaPlayerTopics.VOLUME_SET]
    publish.single(volume_topic, "0.75", hostname="localhost")
    
    assert callback_called.wait(timeout=2.0), "Volume callback was not called"
    assert received_payload == 0.75  # Should be parsed as float


def test_command_routing_shuffle_command():
    """Test shuffle_set command routing with boolean payload parsing"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_shuffle") 
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callback_called = Event()
    received_payload = None
    
    def shuffle_callback(shuffle: bool, client, user_data, message):
        nonlocal received_payload
        # Shuffle is now passed as first parameter, already parsed
        received_payload = shuffle
        callback_called.set()
    
    callbacks: MediaPlayerCallbacks = {
        'shuffle_set': shuffle_callback,
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Send shuffle command
    shuffle_topic = player._topics[MediaPlayerTopics.SHUFFLE_SET]
    publish.single(shuffle_topic, "ON", hostname="localhost")
    
    assert callback_called.wait(timeout=2.0), "Shuffle callback was not called"
    assert received_payload is True  # Should be parsed as boolean


def test_command_routing_no_callback_registered():
    """Test command routing when no callback is registered"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_no_callback")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    # Create player with play callback but not pause
    callbacks: MediaPlayerCallbacks = {
        'play': MagicMock(),
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Try to send pause command (no callback registered)
    # This should not crash but should log a warning
    # Note: pause topic won't exist because no callback was provided
    assert MediaPlayerTopics.PAUSE not in player._topics


def test_command_routing_multiple_commands():
    """Test routing multiple different commands to same player"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_multi")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    play_called = Event()
    pause_called = Event() 
    volume_called = Event()
    
    callbacks: MediaPlayerCallbacks = {
        'play': lambda *args: play_called.set(),
        'pause': lambda *args: pause_called.set(),
        'volume_set': lambda *args: volume_called.set(),
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Send multiple commands
    publish.single(player._topics[MediaPlayerTopics.PLAY], "PLAY", hostname="localhost")
    publish.single(player._topics[MediaPlayerTopics.PAUSE], "PAUSE", hostname="localhost") 
    publish.single(player._topics[MediaPlayerTopics.VOLUME_SET], "0.5", hostname="localhost")
    
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
    player = MediaPlayer(settings, {})
    
    valid_states = ['playing', 'paused', 'stopped', 'idle', 'off']
    
    # Should not raise exceptions
    for state in valid_states:
        player.set_state(state)


def test_set_state_invalid():
    """Test setting invalid player state"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_invalid_state")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    with pytest.raises(ValueError, match="Invalid state 'invalid'"):
        player.set_state("invalid")


def test_set_volume_valid():
    """Test setting valid volume levels"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_volume_valid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    # Test boundary values
    player.set_volume(0.0)
    player.set_volume(1.0)
    player.set_volume(0.5)


def test_set_volume_invalid():
    """Test setting invalid volume levels"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_volume_invalid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    with pytest.raises(ValueError, match="Volume must be between 0.0 and 1.0"):
        player.set_volume(-0.1)
        
    with pytest.raises(ValueError, match="Volume must be between 0.0 and 1.0"):
        player.set_volume(1.1)


def test_set_position_valid():
    """Test setting valid playback position"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_position_valid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    player.set_position(0)
    player.set_position(30)
    player.set_position(120)


def test_set_position_invalid():
    """Test setting invalid playback position"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_position_invalid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    with pytest.raises(ValueError, match="Position must be non-negative"):
        player.set_position(-1)


def test_set_duration_valid():
    """Test setting valid media duration"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_duration_valid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    player.set_duration(0)
    player.set_duration(180)
    player.set_duration(3600)


def test_set_duration_invalid():
    """Test setting invalid media duration"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_duration_invalid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    with pytest.raises(ValueError, match="Duration must be non-negative"):
        player.set_duration(-1)


def test_set_media_metadata():
    """Test setting media metadata"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_metadata")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    # Should not raise exceptions
    player.set_title("Test Song")
    player.set_artist("Test Artist")
    player.set_album("Test Album")
    player.set_albumart_url("http://example.com/art.jpg")
    player.set_media_image_remotely_accessible(True)
    player.set_media_image_remotely_accessible(False)


def test_set_shuffle_without_support():
    """Test setting shuffle when not supported"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_shuffle_unsupported")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})  # No shuffle_set callback
    
    with pytest.raises(RuntimeError, match="Player does not support shuffle control"):
        player.set_shuffle(True)


def test_set_shuffle_with_support():
    """Test setting shuffle when supported"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_shuffle_supported")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callbacks: MediaPlayerCallbacks = {
        'shuffle_set': MagicMock(),
    }
    player = MediaPlayer(settings, callbacks)
    
    # Should not raise exceptions
    player.set_shuffle(True)
    player.set_shuffle(False)


def test_set_repeat_without_support():
    """Test setting repeat when not supported"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_repeat_unsupported")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})  # No repeat_set callback
    
    with pytest.raises(RuntimeError, match="Player does not support repeat control"):
        player.set_repeat("all")


def test_set_repeat_with_support():
    """Test setting repeat when supported"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_repeat_supported")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callbacks: MediaPlayerCallbacks = {
        'repeat_set': MagicMock(),
    }
    player = MediaPlayer(settings, callbacks)
    
    valid_modes = ['off', 'all', 'one']
    for mode in valid_modes:
        player.set_repeat(mode)


def test_set_repeat_invalid_mode():
    """Test setting invalid repeat mode"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_repeat_invalid")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callbacks: MediaPlayerCallbacks = {
        'repeat_set': MagicMock(),
    }
    player = MediaPlayer(settings, callbacks)
    
    with pytest.raises(ValueError, match="Invalid repeat mode 'invalid'"):
        player.set_repeat("invalid")


def test_update_media_info():
    """Test bulk media info update"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_bulk_media")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    # Should not raise exceptions
    player.update_media_info(
        title="Test Song",
        duration=240,
        artist="Test Artist",
        album="Test Album",
        albumart_url="http://example.com/art.jpg",
        media_image_remotely_accessible=True
    )


def test_update_media_info_minimal():
    """Test bulk media info update with minimal parameters"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_bulk_minimal")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    # Should use defaults for unspecified parameters
    player.update_media_info(
        title="Minimal Song",
        duration=180
    )


def test_update_playback_state():
    """Test bulk playback state update"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_bulk_playback")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callbacks: MediaPlayerCallbacks = {
        'shuffle_set': MagicMock(),
        'repeat_set': MagicMock(),
    }
    player = MediaPlayer(settings, callbacks)
    
    # Should not raise exceptions
    player.update_playback_state(
        state="playing",
        volume=0.7,
        muted=False,
        shuffle=True,
        repeat="all"
    )


def test_set_availability():
    """Test setting availability"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="test_availability")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    # Should not raise exceptions
    player.set_availability(True)
    player.set_availability(False)


# === Configuration Generation Tests ===


def test_generate_config_minimal_player(minimal_media_player):
    """Test config generation for minimal player"""
    config = minimal_media_player.generate_config()
    
    # Should have basic required fields
    assert config["component"] == "media_player"
    assert config["name"] == "test"
    assert "state_topic" in config
    assert "availability_topic" in config
    assert config["payload_available"] == "online"
    assert config["payload_not_available"] == "offline"
    
    # Should have metadata topics
    metadata_topics = [
        "media_title_topic", "media_artist_topic", "media_album_name_topic",
        "media_duration_topic", "media_position_topic", "volume_level_topic",
        "media_image_url_topic", "media_image_remotely_accessible_topic"
    ]
    for topic in metadata_topics:
        assert topic in config
    
    # Should NOT have command topics
    command_topics = [
        "play_topic", "pause_topic", "stop_topic", "next_track_topic",
        "previous_track_topic", "volume_set_topic", "seek_topic"
    ]
    for topic in command_topics:
        assert topic not in config


def test_generate_config_full_player(full_featured_media_player):
    """Test config generation for full-featured player"""
    config = full_featured_media_player.generate_config()
    
    # Should have all command topics
    expected_command_topics = [
        "play_topic", "pause_topic", "stop_topic",
        "next_track_topic", "previous_track_topic", "volume_set_topic",
        "seek_topic", "volume_mute_topic", "shuffle_set_topic", "repeat_set_topic",
        "select_source_topic", "select_sound_mode_topic",
        "turn_on_topic", "turn_off_topic", "play_media_topic", "browse_media_topic"
    ]
    
    for topic in expected_command_topics:
        assert topic in config, f"Missing command topic: {topic}"
    
    # Should also have all metadata topics
    expected_metadata_topics = [
        "media_title_topic", "media_artist_topic", "media_album_name_topic",
        "media_duration_topic", "media_position_topic", "volume_level_topic",
        "media_image_url_topic", "media_image_remotely_accessible_topic"
    ]
    
    for topic in expected_metadata_topics:
        assert topic in config, f"Missing metadata topic: {topic}"


def test_generate_config_partial_player(partial_media_player):
    """Test config generation for partial player"""
    config = partial_media_player.generate_config()
    
    # Should have only relevant command topics
    expected_command_topics = ["play_topic", "pause_topic", "volume_set_topic", "shuffle_set_topic"]
    unexpected_command_topics = ["stop_topic", "next_track_topic", "seek_topic", "repeat_set_topic"]
    
    for topic in expected_command_topics:
        assert topic in config, f"Missing expected topic: {topic}"
        
    for topic in unexpected_command_topics:
        assert topic not in config, f"Unexpected topic present: {topic}"


def test_generate_config_with_device(media_player_with_device):
    """Test config generation includes device info"""
    config = media_player_with_device.generate_config()
    
    # Should include device information
    assert "device" in config
    assert config["device"]["name"] == "test_device"
    assert config["device"]["identifiers"] == "test_device_id"
    assert config["unique_id"] == "test_living_room"


def test_generate_config_topic_urls():
    """Test that generated config contains proper topic URLs"""
    mqtt_settings = Settings.MQTT(host="localhost", state_prefix="homeassistant")
    entity_info = MediaPlayerInfo(name="config_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callbacks: MediaPlayerCallbacks = {
        'play': MagicMock(),
        'volume_set': MagicMock(),
    }
    player = MediaPlayer(settings, callbacks)
    
    config = player.generate_config()
    
    # Verify topic URLs follow expected pattern
    assert config["state_topic"] == "homeassistant/media_player/config_test/state"
    assert config["play_topic"] == "homeassistant/media_player/config_test/play"
    assert config["volume_set_topic"] == "homeassistant/media_player/config_test/volume_set"
    assert config["media_title_topic"] == "homeassistant/media_player/config_test/title"


def test_generate_config_with_device_in_topic_path():
    """Test config generation with device affecting topic paths"""
    device = DeviceInfo(name="Living Room TV", identifiers="lr_tv_001")
    mqtt_settings = Settings.MQTT(host="localhost", state_prefix="ha")
    entity_info = MediaPlayerInfo(name="Main Player", device=device, unique_id="lr_main_player")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    callbacks: MediaPlayerCallbacks = {
        'play': MagicMock(),
    }
    player = MediaPlayer(settings, callbacks)
    
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
        'play': MagicMock(),
        'pause': MagicMock(),
        'volume_set': MagicMock(),
    }
    player = MediaPlayer(settings, callbacks)
    
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
    received_command = {}
    
    def play_handler(client, user_data, message):
        received_command['topic'] = message.topic
        received_command['payload'] = message.payload.decode()
        command_received.set()
    
    callbacks: MediaPlayerCallbacks = {
        'play': play_handler,
        'pause': MagicMock(),
        'volume_set': MagicMock(),
    }
    
    # 1. Create and connect player
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)  # Allow connection
    
    # 2. Publish state updates
    player.set_state("playing")
    player.set_title("Test Song")
    player.set_artist("Test Artist")
    player.set_volume(0.8)
    player.set_availability(True)
    
    # 3. Send command via MQTT
    play_topic = player._topics[MediaPlayerTopics.PLAY]
    publish.single(play_topic, "PLAY", hostname="localhost")
    
    # 4. Verify command was received and processed
    assert command_received.wait(timeout=2.0), "Play command not received"
    assert received_command['topic'] == play_topic
    assert received_command['payload'] == "PLAY"
    
    # 5. Verify player state can be updated after command
    player.set_state("paused")
    player.set_position(30)


def test_multiple_players_isolated_commands():
    """Test that multiple players receive only their own commands"""
    mqtt_settings = Settings.MQTT(host="localhost")
    
    # Create two players with different names
    player1_received = Event()
    player2_received = Event()
    
    def player1_handler(client, user_data, message):
        player1_received.set()
    
    def player2_handler(client, user_data, message):
        player2_received.set()
    
    # Player 1
    entity_info1 = MediaPlayerInfo(name="isolated_test_1")
    settings1 = Settings(mqtt=mqtt_settings, entity=entity_info1)
    callbacks1: MediaPlayerCallbacks = {'play': player1_handler}
    player1 = MediaPlayer(settings1, callbacks1)
    
    # Player 2
    entity_info2 = MediaPlayerInfo(name="isolated_test_2") 
    settings2 = Settings(mqtt=mqtt_settings, entity=entity_info2)
    callbacks2: MediaPlayerCallbacks = {'play': player2_handler}
    player2 = MediaPlayer(settings2, callbacks2)
    
    time.sleep(0.5)  # Allow connections
    
    # Send command only to player1
    play_topic1 = player1._topics[MediaPlayerTopics.PLAY]
    publish.single(play_topic1, "PLAY", hostname="localhost")
    
    # Only player1 should receive the command
    assert player1_received.wait(timeout=2.0), "Player1 did not receive its command"
    assert not player2_received.is_set(), "Player2 incorrectly received player1's command"


def test_player_with_device_end_to_end():
    """Test end-to-end flow for player with device info"""
    device = DeviceInfo(name="Test Device", identifiers="test_device_123")
    mqtt_settings = Settings.MQTT(host="localhost", state_prefix="test")
    entity_info = MediaPlayerInfo(name="Device Player", device=device, unique_id="device_player_001")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    volume_command_received = Event()
    received_volume = None
    
    def volume_handler(volume: float, client, user_data, message):
        nonlocal received_volume
        # Volume is now passed as first parameter, already parsed
        received_volume = volume
        volume_command_received.set()
    
    callbacks: MediaPlayerCallbacks = {
        'volume_set': volume_handler,
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Verify device info in config
    config = player.generate_config()
    assert config["device"]["name"] == "Test Device"
    assert config["unique_id"] == "device_player_001"
    
    # Test command with device-specific topic path (spaces become dashes)
    volume_topic = player._topics[MediaPlayerTopics.VOLUME_SET]
    assert "/test-device/device-player/" in volume_topic
    
    # Send volume command
    publish.single(volume_topic, "0.65", hostname="localhost")
    
    assert volume_command_received.wait(timeout=2.0), "Volume command not received"
    assert received_volume == 0.65  # Parsed as float


def test_error_handling_in_command_flow():
    """Test error handling during command processing"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="error_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    # Create callback that raises an exception
    def error_callback(client, user_data, message):
        raise ValueError("Test error in callback")
    
    callbacks: MediaPlayerCallbacks = {
        'play': error_callback,
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Send command - should not crash the player
    play_topic = player._topics[MediaPlayerTopics.PLAY]
    publish.single(play_topic, "PLAY", hostname="localhost")
    
    time.sleep(0.5)  # Allow error processing
    
    # Player should still be functional for state updates
    player.set_state("idle")  # Should not raise exception


def test_rapid_command_sequence():
    """Test handling of rapid command sequence"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="rapid_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    commands_received = []
    commands_lock = Event()
    
    # Different handlers for different command types
    def play_command_handler(client, user_data, message):
        commands_received.append("PLAY")
        if len(commands_received) >= 3:
            commands_lock.set()
    
    def pause_command_handler(client, user_data, message): 
        commands_received.append("PAUSE")
        if len(commands_received) >= 3:
            commands_lock.set()
    
    def volume_command_handler(volume: float, client, user_data, message):
        commands_received.append(volume)
        if len(commands_received) >= 3:
            commands_lock.set()
    
    callbacks: MediaPlayerCallbacks = {
        'play': play_command_handler,
        'pause': pause_command_handler,
        'volume_set': volume_command_handler,
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Send rapid sequence of commands
    publish.single(player._topics[MediaPlayerTopics.PLAY], "PLAY", hostname="localhost")
    publish.single(player._topics[MediaPlayerTopics.PAUSE], "PAUSE", hostname="localhost")
    publish.single(player._topics[MediaPlayerTopics.VOLUME_SET], "0.7", hostname="localhost")
    
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
    player = MediaPlayer(settings, {})
    
    # Volume set commands should parse as float
    assert player._parse_command_payload(MediaPlayerTopics.VOLUME_SET, "0.5") == 0.5
    assert player._parse_command_payload(MediaPlayerTopics.VOLUME_SET, "1.0") == 1.0
    assert player._parse_command_payload(MediaPlayerTopics.VOLUME_SET, "0") == 0.0
    
    # Seek commands should parse as float 
    assert player._parse_command_payload(MediaPlayerTopics.SEEK, "30") == 30.0
    assert player._parse_command_payload(MediaPlayerTopics.SEEK, "120.5") == 120.5


def test_parse_command_payload_boolean_commands():
    """Test payload parsing for boolean commands"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_boolean_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    # Shuffle commands
    assert player._parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "ON") is True
    assert player._parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "OFF") is False
    assert player._parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "on") is True
    assert player._parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "off") is False
    
    # Volume mute commands
    assert player._parse_command_payload(MediaPlayerTopics.VOLUME_MUTE, "ON") is True
    assert player._parse_command_payload(MediaPlayerTopics.VOLUME_MUTE, "OFF") is False


def test_parse_command_payload_string_commands():
    """Test payload parsing for string commands"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_string_test")  
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    # String commands should return raw payload
    assert player._parse_command_payload(MediaPlayerTopics.PLAY, "PLAY") == "PLAY"
    assert player._parse_command_payload(MediaPlayerTopics.PAUSE, "PAUSE") == "PAUSE"
    assert player._parse_command_payload(MediaPlayerTopics.SELECT_SOURCE, "CD Player") == "CD Player"
    assert player._parse_command_payload(MediaPlayerTopics.SELECT_SOURCE, "Bluetooth") == "Bluetooth"
    assert player._parse_command_payload(MediaPlayerTopics.SELECT_SOUND_MODE, "Movie") == "Movie"


def test_parse_command_payload_invalid_numeric():
    """Test payload parsing with invalid numeric values"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_invalid_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    # Invalid numeric payloads should return None
    assert player._parse_command_payload(MediaPlayerTopics.VOLUME_SET, "invalid") is None
    assert player._parse_command_payload(MediaPlayerTopics.VOLUME_SET, "abc") is None
    assert player._parse_command_payload(MediaPlayerTopics.SEEK, "not_a_number") is None


def test_parse_command_payload_edge_cases():
    """Test payload parsing edge cases"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="parse_edge_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    player = MediaPlayer(settings, {})
    
    # Empty strings
    assert player._parse_command_payload(MediaPlayerTopics.PLAY, "") == ""
    assert player._parse_command_payload(MediaPlayerTopics.VOLUME_SET, "") is None  # Invalid float
    
    # Whitespace
    assert player._parse_command_payload(MediaPlayerTopics.SELECT_SOURCE, "  Spotify  ") == "  Spotify  "
    
    # Boolean edge cases
    assert player._parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "True") is False  # Only "ON" is True
    assert player._parse_command_payload(MediaPlayerTopics.SHUFFLE_SET, "1") is False    # Only "ON" is True


def test_payload_parsing_integration_volume():
    """Integration test: volume command with parsed payload"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="integration_volume_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    received_payload = None
    callback_called = Event()
    
    def volume_callback(volume: float, client, user_data, message):
        nonlocal received_payload
        # Volume is now passed as first parameter, already parsed
        received_payload = volume
        callback_called.set()
    
    callbacks: MediaPlayerCallbacks = {
        'volume_set': volume_callback,
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Send string volume, should be parsed to float
    volume_topic = player._topics[MediaPlayerTopics.VOLUME_SET]
    publish.single(volume_topic, "0.85", hostname="localhost")
    
    assert callback_called.wait(timeout=2.0), "Volume callback not called"
    assert received_payload == 0.85
    assert isinstance(received_payload, float)


def test_payload_parsing_integration_boolean():
    """Integration test: shuffle command with parsed payload"""  
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="integration_boolean_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    received_payload = None
    callback_called = Event()
    
    def shuffle_callback(shuffle: bool, client, user_data, message):
        nonlocal received_payload
        # Shuffle is now passed as first parameter, already parsed
        received_payload = shuffle
        callback_called.set()
    
    callbacks: MediaPlayerCallbacks = {
        'shuffle_set': shuffle_callback,
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Send string "OFF", should be parsed to False
    shuffle_topic = player._topics[MediaPlayerTopics.SHUFFLE_SET]
    publish.single(shuffle_topic, "OFF", hostname="localhost")
    
    assert callback_called.wait(timeout=2.0), "Shuffle callback not called"
    assert received_payload is False
    assert isinstance(received_payload, bool)


def test_payload_parsing_integration_string():
    """Integration test: string command with raw payload"""
    mqtt_settings = Settings.MQTT(host="localhost")
    entity_info = MediaPlayerInfo(name="integration_string_test")
    settings = Settings(mqtt=mqtt_settings, entity=entity_info)
    
    received_payload = None
    callback_called = Event()
    
    def source_callback(source: str, client, user_data, message):
        nonlocal received_payload
        # Source is now passed as first parameter, already parsed
        received_payload = source
        callback_called.set()
    
    callbacks: MediaPlayerCallbacks = {
        'select_source': source_callback,
    }
    
    player = MediaPlayer(settings, callbacks)
    time.sleep(0.5)
    
    # Send string source, should remain as string
    source_topic = player._topics[MediaPlayerTopics.SELECT_SOURCE] 
    publish.single(source_topic, "Aux Input", hostname="localhost")
    
    assert callback_called.wait(timeout=2.0), "Source callback not called"
    assert received_payload == "Aux Input"
    assert isinstance(received_payload, str)