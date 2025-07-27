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
        **kwargs
    ):
        mqtt_settings = Settings.MQTT(host="localhost")
        update_info = UpdateInfo(
            name=name,
            device=device,
            unique_id=unique_id,
            latest_version_topic=latest_version_topic,
            **kwargs
        )
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
        mock_publish.assert_called_with(update.state_topic, "1.2.3", retain=True)


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
        update.set_state("1.2.3")

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["installed_version"] == "1.2.3"
        assert "latest_version" not in published_data
        assert "in_progress" not in published_data
        assert "update_percentage" not in published_data


def test_set_state_complete(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state(
            installed="1.2.3",
            latest="1.2.4",
            in_progress=True,
            progress=75
        )

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["installed_version"] == "1.2.3"
        assert published_data["latest_version"] == "1.2.4"
        assert published_data["in_progress"] is True
        assert published_data["update_percentage"] == 75


def test_set_state_invalid_progress(update: Update):
    with pytest.raises(ValueError, match="Progress must be between 0 and 100"):
        update.set_state("1.2.3", progress=150)


def test_set_state_with_progress_zero(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state("1.2.3", progress=0)

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["update_percentage"] == 0


def test_set_state_with_progress_hundred(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update.set_state("1.2.3", progress=100)

        call_args = mock_publish.call_args
        published_data = json.loads(call_args[0][1])

        assert published_data["update_percentage"] == 100


def test_update_state_with_string(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        update._update_state("1.2.3")
        mock_publish.assert_called_with(update.state_topic, "1.2.3", retain=True)


def test_update_state_with_dict(update: Update):
    with patch.object(update.mqtt_client, "publish") as mock_publish:
        state_dict = {"installed_version": "1.2.3", "in_progress": False}
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
