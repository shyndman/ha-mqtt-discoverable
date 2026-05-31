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
from typing import Protocol, cast
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Sensor, SensorInfo


class SensorFactory(Protocol):
    def __call__(self, suggested_display_precision: None | int = 2) -> Sensor: ...


def published_payload(mock_publish: object) -> dict[str, object]:
    publish_mock = cast(Mock, mock_publish)
    call_args = publish_mock.call_args
    assert call_args is not None

    payload = cast(str, call_args.args[1])
    assert isinstance(payload, str)

    parsed_payload = cast(object, json.loads(payload))
    assert isinstance(parsed_payload, dict)
    return cast(dict[str, object], parsed_payload)


@pytest.fixture
def make_sensor() -> SensorFactory:
    def _make_sensor(suggested_display_precision: None | int = 2) -> Sensor:
        mqtt_settings = Settings.MQTT(host="localhost")
        sensor_info = SensorInfo(
            name="test",
            unit_of_measurement="kWh",
            suggested_display_precision=suggested_display_precision,
        )
        settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
        return Sensor(settings)

    return _make_sensor


@pytest.fixture
def sensor(make_sensor: SensorFactory) -> Sensor:
    return make_sensor()


def test_required_config(sensor: Sensor):
    assert sensor is not None


def test_generate_config(sensor: Sensor):
    config = sensor.generate_config()

    assert config is not None
    assert config["unit_of_measurement"] == "kWh"
    assert config["suggested_display_precision"] == 2


def test_update_state(sensor: Sensor):
    with patch.object(sensor.mqtt_client, "publish") as mock_publish:
        sensor.set_state(1)
        mock_publish.assert_called_with(sensor.state_topic, "1", retain=True)


def test_update_state_with_last_reset(sensor: Sensor):
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone(timedelta(hours=1)))
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    with patch.object(sensor.mqtt_client, "publish") as mock_publish:
        sensor.set_state(1, midnight.isoformat())
        parameter_json = published_payload(mock_publish)
        assert parameter_json["last_reset"] == midnight.isoformat()


def test_invalid_suggested_display_precision(make_sensor: SensorFactory):
    with pytest.raises(ValidationError):
        _ = make_sensor(suggested_display_precision=-1)
