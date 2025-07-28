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

from unittest.mock import MagicMock, patch

import pytest

from ha_mqtt_discoverable import DeviceInfo, Settings
from ha_mqtt_discoverable.media_player import MediaPlayer, MediaPlayerInfo


@pytest.fixture
def make_media_player():
    def _make_media_player(
        name: str = "test",
        device: DeviceInfo | None = None,
        unique_id: str | None = None,
        **kwargs,
    ):
        mqtt_settings = Settings.MQTT(host="localhost")
        media_player_info = MediaPlayerInfo(name=name, device=device, unique_id=unique_id, **kwargs)
        settings = Settings(mqtt=mqtt_settings, entity=media_player_info)
        # Define empty command callbacks
        return MediaPlayer(settings, {})

    return _make_media_player


@pytest.fixture
def media_player(make_media_player) -> MediaPlayer:
    return make_media_player()


@pytest.fixture
def media_player_with_device(make_media_player) -> MediaPlayer:
    device = DeviceInfo(name="test_device", identifiers="test_device_id")
    return make_media_player(name="living_room_player", device=device, unique_id="test_living_room_player")


@pytest.fixture
def media_player_with_features(make_media_player) -> MediaPlayer:
    return make_media_player(
        name="full_featured_player",
        supports_play=True,
        supports_pause=True,
        supports_stop=True,
        supports_volume_set=True,
        supports_volume_mute=True,
        supports_next_track=True,
        supports_previous_track=True,
        supports_seek=True,
        supports_turn_on=True,
        supports_turn_off=True,
        supports_play_media=True,
        supports_shuffle_set=True,
        supports_repeat_set=True,
        supports_select_source=True,
        supports_select_sound_mode=True,
        supports_browse_media=True,
    )


def test_required_config():
    mqtt_settings = Settings.MQTT(host="localhost")
    media_player_info = MediaPlayerInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=media_player_info)
    media_player_entity = MediaPlayer(settings, {})
    assert media_player_entity is not None


def test_media_player_with_device_requires_unique_id():
    device = DeviceInfo(name="test_device", identifiers="test_device_id")
    mqtt_settings = Settings.MQTT(host="localhost")

    with pytest.raises(ValueError, match="A unique_id is required if a device is defined"):
        media_player_info = MediaPlayerInfo(name="test", device=device)
        settings = Settings(mqtt=mqtt_settings, entity=media_player_info)
        MediaPlayer(settings, {})


def test_generate_config(media_player: MediaPlayer):
    config = media_player.generate_config()

    assert config is not None
    assert config["component"] == "media_player"
    assert config["name"] == "test"
    assert "state_topic" in config
    assert "availability_topic" in config
    assert config["payload_available"] == "online"
    assert config["payload_not_available"] == "offline"


def test_generate_config_with_device(media_player_with_device: MediaPlayer):
    config = media_player_with_device.generate_config()

    assert config is not None
    assert config["device"]["name"] == "test_device"
    assert config["device"]["identifiers"] == "test_device_id"
    assert config["unique_id"] == "test_living_room_player"


def test_generate_config_with_features(media_player_with_features: MediaPlayer):
    config = media_player_with_features.generate_config()

    # Check that topics are present for supported features
    assert "play_topic" in config
    assert "pause_topic" in config
    assert "stop_topic" in config
    assert "next_topic" in config
    assert "previous_topic" in config
    assert "volume_set_topic" in config
    assert "seek_topic" in config

    # Check metadata topics
    assert "media_title_topic" in config
    assert "media_artist_topic" in config
    assert "media_album_name_topic" in config
    assert "media_duration_topic" in config
    assert "media_position_topic" in config
    assert "volume_level_topic" in config
    assert "media_image_url_topic" in config


def test_set_state_valid(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish") as mock_publish:
        media_player.set_state("playing")
        mock_publish.assert_called_with(media_player._topics["state"], "playing", retain=True)
    assert media_player._entity.state == "playing"


def test_set_state_invalid():
    mqtt_settings = Settings.MQTT(host="localhost")
    media_player_info = MediaPlayerInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=media_player_info)
    media_player_entity = MediaPlayer(settings, {})

    with pytest.raises(ValueError, match="Invalid state 'invalid'"):
        media_player_entity.set_state("invalid")


def test_set_title(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish") as mock_publish:
        media_player.set_title("Test Song")
        mock_publish.assert_called_with(media_player._topics["title"], "Test Song", retain=True)
    assert media_player._entity.media_title == "Test Song"


def test_set_artist(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish") as mock_publish:
        media_player.set_artist("Test Artist")
        mock_publish.assert_called_with(media_player._topics["artist"], "Test Artist", retain=True)
    assert media_player._entity.media_artist == "Test Artist"


def test_set_album(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish") as mock_publish:
        media_player.set_album("Test Album")
        mock_publish.assert_called_with(media_player._topics["album"], "Test Album", retain=True)
    assert media_player._entity.media_album_name == "Test Album"


def test_set_volume_valid(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish") as mock_publish:
        media_player.set_volume(0.5)
        mock_publish.assert_called_with(media_player._topics["volume"], "0.5", retain=True)
    assert media_player._entity.volume_level == 0.5


def test_set_volume_invalid_range(media_player: MediaPlayer):
    with pytest.raises(ValueError, match="Volume must be between 0.0 and 1.0"):
        media_player.set_volume(-0.1)

    with pytest.raises(ValueError, match="Volume must be between 0.0 and 1.0"):
        media_player.set_volume(1.1)


def test_set_position_valid(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish") as mock_publish:
        media_player.set_position(30)
        mock_publish.assert_called_with(media_player._topics["position"], "30", retain=True)
    assert media_player._entity.media_position == 30


def test_set_position_negative(media_player: MediaPlayer):
    with pytest.raises(ValueError, match="Position must be non-negative"):
        media_player.set_position(-1)


def test_set_position_exceeds_duration(media_player: MediaPlayer):
    media_player._entity.media_duration = 100
    with pytest.raises(ValueError, match="Position 150 exceeds duration 100"):
        media_player.set_position(150)


def test_set_duration(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish") as mock_publish:
        media_player.set_duration(240)
        mock_publish.assert_called_with(media_player._topics["duration"], "240", retain=True)
    assert media_player._entity.media_duration == 240


def test_set_duration_negative(media_player: MediaPlayer):
    with pytest.raises(ValueError, match="Duration must be non-negative"):
        media_player.set_duration(-1)


def test_set_albumart_url(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish") as mock_publish:
        media_player.set_albumart_url("http://example.com/art.jpg")
        mock_publish.assert_called_with(media_player._topics["albumart"], "http://example.com/art.jpg", retain=True)
    assert media_player._entity.media_image_url == "http://example.com/art.jpg"


def test_set_muted(media_player: MediaPlayer):
    media_player.set_muted(True)
    assert media_player._entity.is_volume_muted is True

    media_player.set_muted(False)
    assert media_player._entity.is_volume_muted is False


def test_set_shuffle_supported(media_player_with_features: MediaPlayer):
    media_player_with_features.set_shuffle(True)
    assert media_player_with_features._entity.shuffle is True


def test_set_shuffle_not_supported(media_player: MediaPlayer):
    with pytest.raises(RuntimeError, match="Player does not support shuffle control"):
        media_player.set_shuffle(True)


def test_set_repeat_valid(media_player_with_features: MediaPlayer):
    media_player_with_features.set_repeat("all")
    assert media_player_with_features._entity.repeat == "all"


def test_set_repeat_invalid(media_player_with_features: MediaPlayer):
    with pytest.raises(ValueError, match="Invalid repeat mode 'invalid'"):
        media_player_with_features.set_repeat("invalid")


def test_set_repeat_not_supported(media_player: MediaPlayer):
    with pytest.raises(RuntimeError, match="Player does not support repeat control"):
        media_player.set_repeat("all")


def test_set_availability(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish") as mock_publish:
        media_player.set_availability(True)
        mock_publish.assert_called_with(media_player._topics["availability"], "online", retain=True)

        media_player.set_availability(False)
        mock_publish.assert_called_with(media_player._topics["availability"], "offline", retain=True)


def test_update_media_info(media_player: MediaPlayer):
    with patch.object(media_player, "set_title") as mock_set_title, \
         patch.object(media_player, "set_artist") as mock_set_artist, \
         patch.object(media_player, "set_album") as mock_set_album, \
         patch.object(media_player, "set_duration") as mock_set_duration, \
         patch.object(media_player, "set_position") as mock_set_position, \
         patch.object(media_player, "set_albumart_url") as mock_set_albumart:

        media_player.update_media_info(
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            duration=240,
            position=30,
            albumart_url="http://example.com/art.jpg"
        )

        mock_set_title.assert_called_once_with("Test Song")
        mock_set_artist.assert_called_once_with("Test Artist")
        mock_set_album.assert_called_once_with("Test Album")
        mock_set_duration.assert_called_once_with(240)
        mock_set_position.assert_called_once_with(30)
        mock_set_albumart.assert_called_once_with("http://example.com/art.jpg")


def test_update_playback_state(media_player_with_features: MediaPlayer):
    with patch.object(media_player_with_features, "set_state") as mock_set_state, \
         patch.object(media_player_with_features, "set_volume") as mock_set_volume, \
         patch.object(media_player_with_features, "set_muted") as mock_set_muted, \
         patch.object(media_player_with_features, "set_shuffle") as mock_set_shuffle, \
         patch.object(media_player_with_features, "set_repeat") as mock_set_repeat:

        media_player_with_features.update_playback_state(
            state="playing",
            volume=0.7,
            muted=False,
            shuffle=True,
            repeat="all"
        )

        mock_set_state.assert_called_once_with("playing")
        mock_set_volume.assert_called_once_with(0.7)
        mock_set_muted.assert_called_once_with(False)
        mock_set_shuffle.assert_called_once_with(True)
        mock_set_repeat.assert_called_once_with("all")


def test_command_callback_handler_play(media_player_with_features: MediaPlayer):
    callback = MagicMock()
    media_player_with_features._command_callbacks["play"] = callback

    message = MagicMock()
    message.topic = media_player_with_features._topics["play"]
    message.payload.decode.return_value = "PLAY"

    media_player_with_features._command_callback_handler(None, None, message)
    callback.assert_called_once_with(None, None, message, "PLAY")


def test_command_callback_handler_volume_set(media_player_with_features: MediaPlayer):
    callback = MagicMock()
    media_player_with_features._command_callbacks["volume_set"] = callback

    message = MagicMock()
    message.topic = media_player_with_features._topics["volumeset"]
    message.payload.decode.return_value = "0.5"

    media_player_with_features._command_callback_handler(None, None, message)
    callback.assert_called_once_with(None, None, message, 0.5)


def test_command_callback_handler_shuffle_set(media_player_with_features: MediaPlayer):
    callback = MagicMock()
    media_player_with_features._command_callbacks["shuffle_set"] = callback

    message = MagicMock()
    message.topic = media_player_with_features._topics["shuffle"]
    message.payload.decode.return_value = "ON"

    media_player_with_features._command_callback_handler(None, None, message)
    callback.assert_called_once_with(None, None, message, True)


def test_command_callback_handler_no_callback(media_player_with_features: MediaPlayer):
    message = MagicMock()
    message.topic = media_player_with_features._topics["play"]
    message.payload.decode.return_value = "PLAY"

    # No callback registered - should log warning but not crash
    media_player_with_features._command_callback_handler(None, None, message)


def test_parse_command_payload_numeric():
    mqtt_settings = Settings.MQTT(host="localhost")
    media_player_info = MediaPlayerInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=media_player_info)
    media_player_entity = MediaPlayer(settings, {})

    assert media_player_entity._parse_command_payload("volume_set", "0.5") == 0.5
    assert media_player_entity._parse_command_payload("seek", "30") == 30.0


def test_parse_command_payload_boolean():
    mqtt_settings = Settings.MQTT(host="localhost")
    media_player_info = MediaPlayerInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=media_player_info)
    media_player_entity = MediaPlayer(settings, {})

    assert media_player_entity._parse_command_payload("shuffle_set", "ON") is True
    assert media_player_entity._parse_command_payload("shuffle_set", "OFF") is False
    assert media_player_entity._parse_command_payload("mute", "ON") is True


def test_parse_command_payload_string():
    mqtt_settings = Settings.MQTT(host="localhost")
    media_player_info = MediaPlayerInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=media_player_info)
    media_player_entity = MediaPlayer(settings, {})

    assert media_player_entity._parse_command_payload("select_source", "CD") == "CD"


def test_topics_structure(media_player: MediaPlayer):
    # Verify topic structure follows the pattern
    assert "/media_player/" in media_player._topics["state"]
    assert media_player._topics["state"].endswith("/state")
    assert media_player._topics["title"].endswith("/title")
    assert media_player._topics["artist"].endswith("/artist")
    assert media_player._topics["volume"].endswith("/volume")


def test_topics_with_device(media_player_with_device: MediaPlayer):
    # Should include device name in topic structure
    assert "/test_device/" in media_player_with_device._topics["state"]
    assert "/test_device/" in media_player_with_device._topics["title"]
    assert "/test_device/" in media_player_with_device._topics["volume"]


def test_topics_with_features(media_player_with_features: MediaPlayer):
    # Command topics should only exist for supported features
    assert "play" in media_player_with_features._topics
    assert "pause" in media_player_with_features._topics
    assert "stop" in media_player_with_features._topics
    assert "volumeset" in media_player_with_features._topics
    assert "seek" in media_player_with_features._topics


def test_minimal_feature_player_has_no_command_topics(media_player: MediaPlayer):
    # Player with no features should not have command topics
    command_topics = ["play", "pause", "stop", "next", "previous", "volumeset", "seek"]
    for topic in command_topics:
        assert topic not in media_player._topics


def test_component_type():
    media_player_info = MediaPlayerInfo(name="test")
    assert media_player_info.component == "media_player"


def test_state_validation_all_valid_states():
    mqtt_settings = Settings.MQTT(host="localhost")
    media_player_info = MediaPlayerInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=media_player_info)
    media_player_entity = MediaPlayer(settings, {})

    valid_states = ['playing', 'paused', 'stopped', 'idle', 'off']

    with patch.object(media_player_entity.mqtt_client, "publish"):
        for state in valid_states:
            media_player_entity.set_state(state)
            assert media_player_entity._entity.state == state


def test_repeat_mode_validation():
    mqtt_settings = Settings.MQTT(host="localhost")
    media_player_info = MediaPlayerInfo(name="test", supports_repeat_set=True)
    settings = Settings(mqtt=mqtt_settings, entity=media_player_info)
    media_player_entity = MediaPlayer(settings, {})

    valid_modes = ['off', 'all', 'one']

    for mode in valid_modes:
        media_player_entity.set_repeat(mode)
        assert media_player_entity._entity.repeat == mode


def test_volume_boundary_values(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish"):
        # Test boundary values
        media_player.set_volume(0.0)
        assert media_player._entity.volume_level == 0.0

        media_player.set_volume(1.0)
        assert media_player._entity.volume_level == 1.0


def test_position_with_duration_boundary(media_player: MediaPlayer):
    with patch.object(media_player.mqtt_client, "publish"):
        media_player.set_duration(100)

        # Position equal to duration should be allowed
        media_player.set_position(100)
        assert media_player._entity.media_position == 100
