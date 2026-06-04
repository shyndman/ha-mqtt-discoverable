import asyncio
import json
from typing import Protocol, cast

import pytest
from pydantic import ValidationError

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Sensor, SensorInfo
from ._session_stub import RecordingSession


class SensorFactory(Protocol):
    def __call__(
        self, suggested_display_precision: None | int = 2
    ) -> tuple[RecordingSession, Sensor]: ...


@pytest.fixture
def make_sensor() -> SensorFactory:
    def _make_sensor(
        suggested_display_precision: None | int = 2,
    ) -> tuple[RecordingSession, Sensor]:
        session = RecordingSession(
            Settings.MQTT(url="mqtt://localhost", client_name="test")
        )
        sensor_info = SensorInfo(
            name="test",
            unit_of_measurement="kWh",
            suggested_display_precision=suggested_display_precision,
        )
        return session, Sensor(session, sensor_info)

    return _make_sensor


@pytest.fixture
def sensor(make_sensor: SensorFactory) -> tuple[RecordingSession, Sensor]:
    return make_sensor()


def test_required_config(sensor: tuple[RecordingSession, Sensor]):
    _, entity = sensor
    assert entity is not None


def test_generate_config(sensor: tuple[RecordingSession, Sensor]):
    _, entity = sensor
    config = entity.generate_config()

    assert config["unit_of_measurement"] == "kWh"
    assert config["suggested_display_precision"] == 2


def test_update_state(sensor: tuple[RecordingSession, Sensor]):
    session, entity = sensor
    asyncio.run(entity.set_state(1))

    by_topic = {message.topic: message for message in session.published}
    assert by_topic[entity.config_topic].retain is True
    assert by_topic[entity.state_topic].payload == "1"
    assert by_topic[entity.state_topic].retain is True


def test_update_state_with_last_reset(sensor: tuple[RecordingSession, Sensor]):
    from datetime import datetime, timedelta, timezone

    session, entity = sensor
    now = datetime.now(timezone(timedelta(hours=1)))
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    asyncio.run(entity.set_state(1, midnight.isoformat()))
    payload = session.published[-1].payload
    assert isinstance(payload, str)
    parsed_payload = cast(dict[str, object], json.loads(payload))
    assert parsed_payload["last_reset"] == midnight.isoformat()


def test_invalid_suggested_display_precision(make_sensor: SensorFactory):
    with pytest.raises(ValidationError):
        make_sensor(suggested_display_precision=-1)
