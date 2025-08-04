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

import json
from unittest.mock import patch

import pytest

from ha_mqtt_discoverable import DeviceInfo, Settings
from ha_mqtt_discoverable.sensors import Update, UpdateInfo


@pytest.fixture
def make_update():
    def _make_update(
        name: str = "test",
        device: DeviceInfo | None = None,
        unique_id: str | None = None,
        latest_version_topic: str | None = None,
        **kwargs,
    ):
        mqtt_settings = Settings.MQTT(host="localhost")
        update_info = UpdateInfo(name=name, device=device, unique_id=unique_id, latest_version_topic=latest_version_topic, **kwargs)
        settings = Settings(mqtt=mqtt_settings, entity=update_info)
        # Define an empty command_callback
        return Update(settings, lambda *_: None)

    return _make_update


@pytest.fixture
def update(make_update) -> Update:
    return make_update()


@pytest.fixture
def update_with_device(make_update) -> Update:
    device = DeviceInfo(name="test_device", identifiers="test_device_id")
    return make_update(name="firmware_update", device=device, unique_id="test_firmware_update")


def test_required_config():
    mqtt_settings = Settings.MQTT(host="localhost")
    update_info = UpdateInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=update_info)
    # Define empty callback
    update_entity = Update(settings, lambda *_: None)
    assert update_entity is not None


def test_update_with_device_requires_unique_id():
    device = DeviceInfo(name="test_device", identifiers="test_device_id")
    mqtt_settings = Settings.MQTT(host="localhost")

    with pytest.raises(ValueError, match="A unique_id is required if a device is defined"):
        update_info = UpdateInfo(name="test", device=device)
        settings = Settings(mqtt=mqtt_settings, entity=update_info)
        Update(settings, lambda *_: None)


def test_generate_config(update: Update):
    config = update.generate_config()

    assert config is not None
    assert config["component"] == "update"
    assert config["name"] == "test"
    assert config["state_topic"] == update.state_topic
    assert config["command_topic"] == update._command_topic
    assert config["latest_version_topic"] == update._latest_version_topic
    assert config["payload_install"] == "INSTALL"


def test_generate_config_with_device(update_with_device: Update):
    config = update_with_device.generate_config()

    assert config is not None
    assert config["device"]["name"] == "test_device"
    assert config["device"]["identifiers"] == "test_device_id"
    assert config["unique_id"] == "test_firmware_update"


def test_generate_config_with_custom_payload_install(make_update):
    update_entity = make_update(payload_install="UPGRADE")
    config = update_entity.generate_config()

    assert config["payload_install"] == "UPGRADE"


def test_custom_latest_version_topic(make_update):
    custom_topic = "custom/version/topic"
    update_entity = make_update(latest_version_topic=custom_topic)

    assert update_entity._latest_version_topic == custom_topic

    config = update_entity.generate_config()
    assert config["latest_version_topic"] == custom_topic


def test_default_latest_version_topic(update: Update):
    expected_topic = f"{update._settings.mqtt.state_prefix}/{update._entity_topic}/latest_version"
    assert update._latest_version_topic == expected_topic


def test_set_installed_version(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_installed_version("1.2.3")

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["installed_version"] == "1.2.3"
        assert published_data["in_progress"] is False
        assert call_args[0][0] == update.state_topic


def test_set_latest_version(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_latest_version("1.2.4")
        mock_publish.assert_called_with(update._latest_version_topic, "1.2.4", retain=True)


def test_set_progress_valid(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_progress(50)

        # Should publish JSON state with progress
        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["in_progress"] is True
        assert published_data["update_percentage"] == 50
        assert call_args[0][0] == update.state_topic


def test_set_progress_invalid_range(update: Update):
    with pytest.raises(ValueError, match="Progress must be between 0 and 100"):
        update.set_progress(-1)

    with pytest.raises(ValueError, match="Progress must be between 0 and 100"):
        update.set_progress(101)


def test_set_state_minimal(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3")

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        # Should publish JSON with installed_version and in_progress: false
        assert published_data["installed_version"] == "1.2.3"
        assert published_data["in_progress"] is False
        assert "latest_version" not in published_data
        assert "update_percentage" not in published_data
        assert call_args[0][0] == update.state_topic


def test_set_state_with_latest_version_only(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3", latest="1.2.4")

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        # Should publish JSON when latest version is provided
        assert published_data["installed_version"] == "1.2.3"
        assert published_data["latest_version"] == "1.2.4"
        assert published_data["in_progress"] is False
        assert "update_percentage" not in published_data

def test_set_state_in_progress_false_explicit(update: Update):
    """Test that in_progress=False is explicitly published in JSON state"""
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3", latest="1.2.4", in_progress=False)

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        # Should explicitly include in_progress: false
        assert published_data["installed_version"] == "1.2.3"
        assert published_data["latest_version"] == "1.2.4"
        assert published_data["in_progress"] is False
        assert "in_progress" in published_data  # Key should be present
        assert "update_percentage" not in published_data


def test_set_state_complete(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3", latest="1.2.4", in_progress=True, progress=75)

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["installed_version"] == "1.2.3"
        assert published_data["latest_version"] == "1.2.4"
        assert published_data["in_progress"] is True
        assert published_data["update_percentage"] == 75


def test_set_state_invalid_progress(update: Update):
    with pytest.raises(ValueError, match="Progress must be between 0 and 100"):
        update.set_state(installed="1.2.3", progress=150)


def test_set_state_with_progress_zero(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3", progress=0)

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["update_percentage"] == 0


def test_update_without_command_callback():
    """Test that Update entity without command callback doesn't publish command topic"""
    mqtt_settings = Settings.MQTT(host="localhost")
    update_info = UpdateInfo(name="test_readonly")
    settings = Settings(mqtt=mqtt_settings, entity=update_info)

    # Create update without command callback
    update_entity = Update(settings)

    # Generate config
    config = update_entity.generate_config()

    # Assert that command topic is NOT in the config
    assert "command_topic" not in config

    # Assert that other expected fields are still present
    assert config["component"] == "update"
    assert config["name"] == "test_readonly"
    assert config["state_topic"] == update_entity.state_topic
    assert config["latest_version_topic"] == update_entity._latest_version_topic
    assert config["payload_install"] == "INSTALL"


def test_update_with_command_callback():
    """Test that Update entity with command callback publishes command topic (existing behavior)"""
    mqtt_settings = Settings.MQTT(host="localhost")
    update_info = UpdateInfo(name="test_with_callback")
    settings = Settings(mqtt=mqtt_settings, entity=update_info)

    # Create update with command callback
    update_entity = Update(settings, lambda *_: None)

    # Generate config
    config = update_entity.generate_config()

    # Assert that command topic IS in the config
    assert "command_topic" in config
    assert config["command_topic"] == update_entity._command_topic

    # Assert that other expected fields are still present
    assert config["component"] == "update"
    assert config["name"] == "test_with_callback"
    assert config["state_topic"] == update_entity.state_topic
    assert config["latest_version_topic"] == update_entity._latest_version_topic
    assert config["payload_install"] == "INSTALL"


def test_set_state_with_progress_hundred(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3", progress=100)

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["update_percentage"] == 100


def test_update_state_with_typeddict(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        from ha_mqtt_discoverable.sensors import UpdateStatePayload

        state_dict: UpdateStatePayload = {"installed_version": "1.2.3", "in_progress": False}
        update._update_state(state_dict)

        call_args = mock_publish.call_args
        published_data = call_args[0][1]

        # Should be JSON string
        assert isinstance(published_data, str)
        parsed_data = json.loads(published_data)
        assert parsed_data == state_dict


def test_topics_structure(update: Update):
    # Verify topic structure follows the pattern
    assert "/update/" in update.state_topic
    assert "/update/" in update._latest_version_topic
    assert "/update/" in update._command_topic
    assert update.state_topic.endswith("/state")
    assert update._latest_version_topic.endswith("/latest_version")
    assert update._command_topic.endswith("/command")


def test_topics_with_device(update_with_device: Update):
    # Should include device name in topic structure
    assert "/test_device/" in update_with_device.state_topic
    assert "/test_device/" in update_with_device._latest_version_topic
    assert "/test_device/" in update_with_device._command_topic


# Tests for new functionality and JSON validation

def test_update_info_display_precision(make_update):
    """Test that display_precision field is properly handled"""
    update_entity = make_update(display_precision=2)
    assert update_entity._entity.display_precision == 2

    config = update_entity.generate_config()
    assert config["display_precision"] == 2


def test_update_info_entity_picture_in_config(make_update):
    """Test that entity_picture is included in config when specified"""
    picture_url = "https://example.com/picture.png"
    update_entity = make_update(entity_picture=picture_url)

    config = update_entity.generate_config()
    assert config["entity_picture"] == picture_url


def test_update_info_device_class_in_config(make_update):
    """Test that device_class is included in config when specified"""
    update_entity = make_update(device_class="firmware")

    config = update_entity.generate_config()
    assert config["device_class"] == "firmware"


def test_set_state_with_all_metadata(update: Update):
    """Test set_state with all supported metadata fields"""
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(
            installed="1.0.0",
            latest="1.1.0",
            title="Major Update",
            release_summary="This update includes bug fixes and new features",
            release_url="https://example.com/releases/1.1.0",
            entity_picture="https://example.com/icon.png"
        )

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["installed_version"] == "1.0.0"
        assert published_data["latest_version"] == "1.1.0"
        assert published_data["title"] == "Major Update"
        assert published_data["release_summary"] == "This update includes bug fixes and new features"
        assert published_data["release_url"] == "https://example.com/releases/1.1.0"
        assert published_data["entity_picture"] == "https://example.com/icon.png"
        assert published_data["in_progress"] is False


def test_set_state_auto_in_progress_when_progress_set(update: Update):
    """Test that in_progress is automatically set to True when progress is specified"""
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        # Even if we explicitly set in_progress=False, it should be True when progress is set
        update.set_state(installed="1.0.0", in_progress=False, progress=50)

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["update_percentage"] == 50
        assert published_data["in_progress"] is True  # Should be True despite explicit False


def test_json_validation_valid_payload(update: Update):
    """Test that valid JSON payloads pass validation"""
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        # This should not raise any validation errors
        valid_state = {
            "installed_version": "1.0.0",
            "latest_version": "1.1.0",
            "in_progress": False,
            "update_percentage": 50
        }
        update._update_state(valid_state)

        # Should have been published successfully
        assert mock_publish.called


def test_json_validation_invalid_progress_range(update: Update):
    """Test that invalid progress values are caught by validation"""
    with pytest.raises(ValueError, match="Invalid update state payload"):
        update._update_state({
            "installed_version": "1.0.0",
            "update_percentage": 150  # Invalid: > 100
        })


def test_json_validation_invalid_url(update: Update):
    """Test that invalid URLs are caught by validation"""
    with pytest.raises(ValueError, match="Invalid update state payload"):
        update._update_state({
            "installed_version": "1.0.0",
            "release_url": "not-a-valid-url"  # Invalid URL format
        })


def test_json_validation_exclude_none_values(update: Update):
    """Test that None values are excluded from the published JSON"""
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        state_with_nones = {
            "installed_version": "1.0.0",
            "latest_version": None,  # Should be excluded
            "in_progress": False,
            "title": None  # Should be excluded
        }
        update._update_state(state_with_nones)

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert "installed_version" in published_data
        assert "in_progress" in published_data
        assert "latest_version" not in published_data  # None values excluded
        assert "title" not in published_data  # None values excluded


def test_generate_config_includes_all_ha_options(make_update):
    """Test that generate_config includes all configured HA options"""
    update_entity = make_update(
        display_precision=1,
        device_class="firmware",
        entity_picture="https://example.com/pic.png",
        latest_version_template="{{ value_json.version }}",
        release_summary="Test summary",
        release_url="https://example.com/release",
        title="Test Update",
        value_template="{{ value_json.current }}",
        payload_install="UPDATE_NOW"
    )

    config = update_entity.generate_config()

    assert config["display_precision"] == 1
    assert config["device_class"] == "firmware"
    assert config["entity_picture"] == "https://example.com/pic.png"
    assert config["latest_version_template"] == "{{ value_json.version }}"
    assert config["release_summary"] == "Test summary"
    assert config["release_url"] == "https://example.com/release"
    assert config["title"] == "Test Update"
    assert config["value_template"] == "{{ value_json.current }}"
    assert config["payload_install"] == "UPDATE_NOW"


def test_typeddict_validation_directly():
    """Test the UpdateStatePayload TypedDict with TypeAdapter validation"""
    from ha_mqtt_discoverable.sensors import UpdateStatePayload, update_state_validator

    # Valid payload
    valid_data: UpdateStatePayload = {
        "installed_version": "1.0.0",
        "latest_version": "1.1.0",
        "update_percentage": 50,
        "in_progress": True,
        "release_url": "https://example.com/release"
    }

    # Should validate without error
    validated = update_state_validator.validate_python(valid_data)
    assert validated["installed_version"] == "1.0.0"
    assert validated["latest_version"] == "1.1.0"
    assert validated["update_percentage"] == 50
    assert validated["in_progress"] is True
    assert str(validated["release_url"]) == "https://example.com/release"


def test_typeddict_validation_invalid_percentage():
    """Test that invalid percentage values are rejected"""
    from ha_mqtt_discoverable.sensors import update_state_validator
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"update_percentage": 150})  # > 100

    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"update_percentage": -10})  # < 0


def test_typeddict_validation_invalid_url():
    """Test that invalid URLs are rejected"""
    from ha_mqtt_discoverable.sensors import update_state_validator
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"release_url": "not-a-url"})

    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"entity_picture": "also-not-a-url"})


def test_update_state_logs_validation_errors(update: Update):
    """Test that validation errors are properly logged"""
    with patch("ha_mqtt_discoverable.sensors.logger") as mock_logger:
        with pytest.raises(ValueError):
            invalid_state = {"update_percentage": 150}
            update._update_state(invalid_state)

        # Should have logged the validation error
        mock_logger.error.assert_called_once()
        assert "Invalid update state payload" in str(mock_logger.error.call_args)


def test_update_state_logs_debug_for_valid_payload(update: Update):
    """Test that successful validation logs debug info"""
    with patch.object(update.mqtt_client, "publish"):
        with patch("ha_mqtt_discoverable.sensors.logger") as mock_logger:
            valid_state = {"installed_version": "1.0.0", "in_progress": False}
            update._update_state(valid_state)

            # Should have logged debug info about validation
            mock_logger.debug.assert_called_once()
            assert "Validated update state payload" in str(mock_logger.debug.call_args)
