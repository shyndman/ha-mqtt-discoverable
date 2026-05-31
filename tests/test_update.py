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
from collections.abc import Callable, Mapping
from typing import Protocol, TypedDict, Unpack, cast
from unittest.mock import Mock, patch

import pytest
from paho.mqtt.client import Client, MQTTMessage

from ha_mqtt_discoverable import DeviceInfo, Settings
from ha_mqtt_discoverable.sensors import Update, UpdateInfo, UpdateStatePayload


class MakeUpdateKwargs(TypedDict, total=False):
    """Optional UpdateInfo fields not covered by _make_update's explicit parameters."""

    # EntityInfo optional fields
    enabled_by_default: bool
    entity_category: str
    expire_after: int
    force_update: bool
    icon: str
    object_id: str
    qos: int
    # UpdateInfo-specific fields
    device_class: str
    display_precision: int
    entity_picture: str
    latest_version_template: str
    payload_install: str
    release_summary: str
    release_url: str
    title: str
    value_template: str


class UpdateFactory(Protocol):
    def __call__(
        self,
        name: str = "test",
        device: DeviceInfo | None = None,
        unique_id: str | None = None,
        latest_version_topic: str | None = None,
        **kwargs: Unpack[MakeUpdateKwargs],
    ) -> Update: ...


def noop_command_callback(
    _client: Client, _user_data: object | None, _message: MQTTMessage
) -> None:
    pass


def config_string(config: Mapping[str, object], key: str) -> str:
    value = config[key]
    assert isinstance(value, str)
    return value


def config_mapping(config: Mapping[str, object], key: str) -> dict[str, object]:
    value = config[key]
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def published_topic(mock_publish: object) -> str:
    publish_mock = cast(Mock, mock_publish)
    call_args = publish_mock.call_args
    assert call_args is not None

    topic = cast(str, call_args.args[0])
    assert isinstance(topic, str)
    return topic


def published_payload(mock_publish: object) -> dict[str, object]:
    publish_mock = cast(Mock, mock_publish)
    call_args = publish_mock.call_args
    assert call_args is not None

    payload = cast(str, call_args.args[1])
    assert isinstance(payload, str)

    parsed_payload = cast(object, json.loads(payload))
    assert isinstance(parsed_payload, dict)
    return cast(dict[str, object], parsed_payload)


def invoke_update_state(update: Update, state: Mapping[str, object]) -> None:
    state_updater = cast(
        Callable[[Mapping[str, object]], None],
        object.__getattribute__(update, "_update_state"),
    )
    state_updater(state)


def latest_version_topic(update: Update) -> str:
    return config_string(update.generate_config(), "latest_version_topic")


def command_topic(update: Update) -> str:
    return config_string(update.generate_config(), "command_topic")


@pytest.fixture
def make_update() -> UpdateFactory:
    def _make_update(
        name: str = "test",
        device: DeviceInfo | None = None,
        unique_id: str | None = None,
        latest_version_topic: str | None = None,
        **kwargs: Unpack[MakeUpdateKwargs],
    ) -> Update:
        mqtt_settings = Settings.MQTT(host="localhost")
        update_info = UpdateInfo(
            name=name,
            device=device,
            unique_id=unique_id,
            latest_version_topic=latest_version_topic,
            **kwargs,
        )
        settings = Settings(mqtt=mqtt_settings, entity=update_info)
        # Define an empty command_callback
        return Update(settings, noop_command_callback)

    return _make_update


@pytest.fixture
def update(make_update: UpdateFactory) -> Update:
    return make_update()


@pytest.fixture
def update_with_device(make_update: UpdateFactory) -> Update:
    device = DeviceInfo(name="test_device", identifiers="test_device_id")
    return make_update(
        name="firmware_update", device=device, unique_id="test_firmware_update"
    )


def test_required_config():
    mqtt_settings = Settings.MQTT(host="localhost")
    update_info = UpdateInfo(name="test")
    settings = Settings(mqtt=mqtt_settings, entity=update_info)
    # Define empty callback
    update_entity = Update(settings, noop_command_callback)
    assert update_entity is not None


def test_update_with_device_requires_unique_id():
    device = DeviceInfo(name="test_device", identifiers="test_device_id")
    mqtt_settings = Settings.MQTT(host="localhost")

    with pytest.raises(
        ValueError, match="A unique_id is required if a device is defined"
    ):
        update_info = UpdateInfo(name="test", device=device)
        settings = Settings(mqtt=mqtt_settings, entity=update_info)
        _ = Update(settings, noop_command_callback)


def test_generate_config(update: Update):
    config = update.generate_config()

    assert config is not None
    assert config["component"] == "update"
    assert config["name"] == "test"
    assert config["state_topic"] == update.state_topic
    assert config["command_topic"] == command_topic(update)
    assert config["latest_version_topic"] == latest_version_topic(update)
    assert config["payload_install"] == "INSTALL"


def test_generate_config_with_device(update_with_device: Update):
    config = update_with_device.generate_config()
    device_config = config_mapping(config, "device")

    assert config is not None
    assert device_config["name"] == "test_device"
    assert device_config["identifiers"] == "test_device_id"
    assert config["unique_id"] == "test_firmware_update"


def test_generate_config_with_custom_payload_install(make_update: UpdateFactory):
    update_entity = make_update(payload_install="UPGRADE")
    config = update_entity.generate_config()

    assert config["payload_install"] == "UPGRADE"


def test_custom_latest_version_topic(make_update: UpdateFactory):
    custom_topic = "custom/version/topic"
    update_entity = make_update(latest_version_topic=custom_topic)

    assert latest_version_topic(update_entity) == custom_topic

    config = update_entity.generate_config()
    assert config["latest_version_topic"] == custom_topic


def test_default_latest_version_topic(update: Update):
    expected_topic = update.state_topic.removesuffix("/state") + "/latest_version"
    assert latest_version_topic(update) == expected_topic


def test_set_installed_version(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_installed_version("1.2.3")

        published_data = published_payload(mock_publish)

        assert published_data["installed_version"] == "1.2.3"
        assert published_data["in_progress"] is False
        assert published_topic(mock_publish) == update.state_topic


def test_set_latest_version(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_latest_version("1.2.4")
        mock_publish.assert_called_with(
            latest_version_topic(update), "1.2.4", retain=True
        )


def test_set_progress_valid(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_progress(50)

        # Should publish JSON state with progress
        published_data = published_payload(mock_publish)

        assert published_data["in_progress"] is True
        assert published_data["update_percentage"] == 50
        assert published_topic(mock_publish) == update.state_topic


def test_set_progress_invalid_range(update: Update):
    with pytest.raises(ValueError, match="Progress must be between 0 and 100"):
        update.set_progress(-1)

    with pytest.raises(ValueError, match="Progress must be between 0 and 100"):
        update.set_progress(101)


def test_set_state_minimal(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3")

        published_data = published_payload(mock_publish)

        # Should publish JSON with installed_version and in_progress: false
        assert published_data["installed_version"] == "1.2.3"
        assert published_data["in_progress"] is False
        assert "latest_version" not in published_data
        assert "update_percentage" not in published_data
        assert published_topic(mock_publish) == update.state_topic


def test_set_state_with_latest_version_only(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3", latest="1.2.4")

        published_data = published_payload(mock_publish)

        # Should publish JSON when latest version is provided
        assert published_data["installed_version"] == "1.2.3"
        assert published_data["latest_version"] == "1.2.4"
        assert published_data["in_progress"] is False
        assert "update_percentage" not in published_data


def test_set_state_in_progress_false_explicit(update: Update):
    """Test that in_progress=False is explicitly published in JSON state"""
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3", latest="1.2.4", in_progress=False)

        published_data = published_payload(mock_publish)

        # Should explicitly include in_progress: false
        assert published_data["installed_version"] == "1.2.3"
        assert published_data["latest_version"] == "1.2.4"
        assert published_data["in_progress"] is False
        assert "in_progress" in published_data  # Key should be present
        assert "update_percentage" not in published_data


def test_set_state_complete(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(
            installed="1.2.3", latest="1.2.4", in_progress=True, progress=75
        )

        published_data = published_payload(mock_publish)

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

        published_data = published_payload(mock_publish)

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
    assert config["latest_version_topic"] == latest_version_topic(update_entity)
    assert config["payload_install"] == "INSTALL"


def test_update_with_command_callback():
    """Test that Update entity with command callback publishes command topic (existing behavior)"""
    mqtt_settings = Settings.MQTT(host="localhost")
    update_info = UpdateInfo(name="test_with_callback")
    settings = Settings(mqtt=mqtt_settings, entity=update_info)

    # Create update with command callback
    update_entity = Update(settings, noop_command_callback)

    # Generate config
    config = update_entity.generate_config()

    # Assert that command topic IS in the config
    assert "command_topic" in config
    assert config["command_topic"] == command_topic(update_entity)

    # Assert that other expected fields are still present
    assert config["component"] == "update"
    assert config["name"] == "test_with_callback"
    assert config["state_topic"] == update_entity.state_topic
    assert config["latest_version_topic"] == latest_version_topic(update_entity)
    assert config["payload_install"] == "INSTALL"


def test_set_state_with_progress_hundred(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(installed="1.2.3", progress=100)

        published_data = published_payload(mock_publish)

        assert published_data["update_percentage"] == 100


def test_update_state_with_typeddict(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        state_dict: UpdateStatePayload = {
            "installed_version": "1.2.3",
            "in_progress": False,
        }
        invoke_update_state(update, state_dict)

        assert published_payload(mock_publish) == state_dict


def test_topics_structure(update: Update):
    # Verify topic structure follows the pattern
    current_latest_version_topic = latest_version_topic(update)
    current_command_topic = command_topic(update)

    assert "/update/" in update.state_topic
    assert "/update/" in current_latest_version_topic
    assert "/update/" in current_command_topic
    assert update.state_topic.endswith("/state")
    assert current_latest_version_topic.endswith("/latest_version")
    assert current_command_topic.endswith("/command")


def test_topics_with_device(update_with_device: Update):
    # Should include device name in topic structure
    assert "/test_device/" in update_with_device.state_topic
    assert "/test_device/" in latest_version_topic(update_with_device)
    assert "/test_device/" in command_topic(update_with_device)


# Tests for new functionality and JSON validation


def test_update_info_display_precision(make_update: UpdateFactory):
    """Test that display_precision field is properly handled"""
    update_entity = make_update(display_precision=2)

    config = update_entity.generate_config()
    assert config["display_precision"] == 2


def test_update_info_entity_picture_in_config(make_update: UpdateFactory):
    """Test that entity_picture is included in config when specified"""
    picture_url = "https://example.com/picture.png"
    update_entity = make_update(entity_picture=picture_url)

    config = update_entity.generate_config()
    assert config["entity_picture"] == picture_url


def test_update_info_device_class_in_config(make_update: UpdateFactory):
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
            entity_picture="https://example.com/icon.png",
        )

        published_data = published_payload(mock_publish)

        assert published_data["installed_version"] == "1.0.0"
        assert published_data["latest_version"] == "1.1.0"
        assert published_data["title"] == "Major Update"
        assert (
            published_data["release_summary"]
            == "This update includes bug fixes and new features"
        )
        assert published_data["release_url"] == "https://example.com/releases/1.1.0"
        assert published_data["entity_picture"] == "https://example.com/icon.png"
        assert published_data["in_progress"] is False


def test_set_state_auto_in_progress_when_progress_set(update: Update):
    """Test that in_progress is automatically set to True when progress is specified"""
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        # Even if we explicitly set in_progress=False, it should be True when progress is set
        update.set_state(installed="1.0.0", in_progress=False, progress=50)

        published_data = published_payload(mock_publish)

        assert published_data["update_percentage"] == 50
        assert (
            published_data["in_progress"] is True
        )  # Should be True despite explicit False


def test_json_validation_valid_payload(update: Update):
    """Test that valid JSON payloads pass validation"""
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        # This should not raise any validation errors
        valid_state: UpdateStatePayload = {
            "installed_version": "1.0.0",
            "latest_version": "1.1.0",
            "in_progress": False,
            "update_percentage": 50,
        }
        invoke_update_state(update, valid_state)

        # Should have been published successfully
        assert mock_publish.called


def test_json_validation_invalid_progress_range(update: Update):
    """Test that invalid progress values are caught by validation"""
    with pytest.raises(ValueError, match="Invalid update state payload"):
        invoke_update_state(
            update,
            {
                "installed_version": "1.0.0",
                "update_percentage": 150,  # Invalid: > 100
            },
        )


def test_json_validation_invalid_url(update: Update):
    """Test that invalid URLs are caught by validation"""
    with pytest.raises(ValueError, match="Invalid update state payload"):
        invoke_update_state(
            update, {"installed_version": "1.0.0", "release_url": "not-a-valid-url"}
        )


def test_json_validation_exclude_none_values(update: Update):
    """Test that None values are excluded from the published JSON"""
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        state_with_nones: dict[str, object] = {
            "installed_version": "1.0.0",
            "latest_version": None,  # Should be excluded
            "in_progress": False,
            "title": None,  # Should be excluded
        }
        invoke_update_state(update, state_with_nones)

        published_data = published_payload(mock_publish)

        assert "installed_version" in published_data
        assert "in_progress" in published_data
        assert "latest_version" not in published_data  # None values excluded
        assert "title" not in published_data  # None values excluded


def test_generate_config_includes_all_ha_options(make_update: UpdateFactory):
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
        payload_install="UPDATE_NOW",
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
    from pydantic import HttpUrl

    from ha_mqtt_discoverable.sensors import update_state_validator

    # Valid payload
    valid_data: UpdateStatePayload = {
        "installed_version": "1.0.0",
        "latest_version": "1.1.0",
        "update_percentage": 50,
        "in_progress": True,
        "release_url": HttpUrl("https://example.com/release"),
    }

    # Should validate without error
    validated = update_state_validator.validate_python(valid_data)
    assert validated.get("installed_version") == "1.0.0"
    assert validated.get("latest_version") == "1.1.0"
    assert validated.get("update_percentage") == 50
    assert validated.get("in_progress") is True
    assert str(validated.get("release_url")) == "https://example.com/release"


def test_typeddict_validation_invalid_percentage():
    """Test that invalid percentage values are rejected"""
    from pydantic import ValidationError

    from ha_mqtt_discoverable.sensors import update_state_validator

    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"update_percentage": 150})  # > 100

    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"update_percentage": -10})  # < 0


def test_typeddict_validation_invalid_url():
    """Test that invalid URLs are rejected"""
    from pydantic import ValidationError

    from ha_mqtt_discoverable.sensors import update_state_validator

    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"release_url": "not-a-url"})

    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"entity_picture": "also-not-a-url"})


def test_update_state_logs_validation_errors(update: Update):
    """Test that validation errors are properly logged"""
    with patch("ha_mqtt_discoverable._update.logger") as mock_logger:
        with pytest.raises(ValueError):
            invoke_update_state(update, {"update_percentage": 150})

        # Should have logged the validation error
        logger_error = cast(Mock, mock_logger.error)
        logger_error.assert_called_once()
        assert "Invalid update state payload" in str(logger_error.call_args)


def test_update_state_logs_debug_for_valid_payload(update: Update):
    """Test that successful validation logs debug info"""
    with (
        patch.object(update.mqtt_client, "publish"),
        patch("ha_mqtt_discoverable._update.logger") as mock_logger,
    ):
        valid_state: UpdateStatePayload = {
            "installed_version": "1.0.0",
            "in_progress": False,
        }
        invoke_update_state(update, valid_state)

        # Should have logged debug info about validation
        logger_debug = cast(Mock, mock_logger.debug)
        logger_debug.assert_called_once()
        assert "Validated update state payload" in str(logger_debug.call_args)
