import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol, TypedDict, Unpack, cast

import pytest
from pydantic import ValidationError

from ha_mqtt_discoverable import DeviceInfo, Settings
from ha_mqtt_discoverable.sensors import Update, UpdateInfo, UpdateStatePayload
from ._session_stub import PublishedMessage, RecordingSession


class MakeUpdateKwargs(TypedDict, total=False):
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
        *,
        name: str = "test",
        device: DeviceInfo | None = None,
        unique_id: str | None = None,
        latest_version_topic: str | None = None,
        with_callback: bool = True,
        **kwargs: Unpack[MakeUpdateKwargs],
    ) -> tuple[RecordingSession, Update]: ...


async def noop_command_callback(_sender: Update, _message: object) -> None:
    return None


def config_string(config: Mapping[str, object], key: str) -> str:
    value = config[key]
    assert isinstance(value, str)
    return value


def published_payload(message: PublishedMessage) -> dict[str, object]:
    payload = message.payload
    assert isinstance(payload, str)
    parsed = cast(object, json.loads(payload))
    assert isinstance(parsed, dict)
    return cast(dict[str, object], parsed)


async def invoke_update_state(update: Update, state: Mapping[str, object]) -> None:
    state_updater = cast(
        Callable[[Mapping[str, object]], Awaitable[None]],
        object.__getattribute__(update, "_update_state"),
    )
    await state_updater(state)


@pytest.fixture
def make_update() -> UpdateFactory:
    def _make_update(
        *,
        name: str = "test",
        device: DeviceInfo | None = None,
        unique_id: str | None = None,
        latest_version_topic: str | None = None,
        with_callback: bool = True,
        **kwargs: Unpack[MakeUpdateKwargs],
    ) -> tuple[RecordingSession, Update]:
        session = RecordingSession(
            Settings.MQTT(url="mqtt://localhost", client_name="test")
        )
        update_info = UpdateInfo(
            name=name,
            device=device,
            unique_id=unique_id,
            latest_version_topic=latest_version_topic,
            **kwargs,
        )
        callback = noop_command_callback if with_callback else None
        return session, Update(session, update_info, callback)

    return _make_update


@pytest.fixture
def update(make_update: UpdateFactory) -> tuple[RecordingSession, Update]:
    return make_update()


def test_required_config(update: tuple[RecordingSession, Update]):
    _, entity = update
    assert entity is not None


def test_update_with_device_requires_unique_id(make_update: UpdateFactory):
    with pytest.raises(
        ValueError, match="A unique_id is required if a device is defined"
    ):
        make_update(
            device=DeviceInfo(name="test_device", identifiers="test_device_id"),
            with_callback=False,
        )


def test_generate_config(update: tuple[RecordingSession, Update]):
    session, entity = update
    config = entity.generate_config()

    assert config["component"] == "update"
    assert config["name"] == "test"
    assert config["state_topic"] == entity.state_topic
    assert config["command_topic"] == "hmd/update/test/command"
    assert config["latest_version_topic"] == "hmd/update/test/latest_version"
    assert config["payload_install"] == "INSTALL"
    assert len(session.commands) == 1


def test_generate_config_without_callback_omits_command_topic(
    make_update: UpdateFactory,
):
    session, entity = make_update(name="readonly", with_callback=False)
    config = entity.generate_config()

    assert "command_topic" not in config
    assert config["latest_version_topic"] == "hmd/update/readonly/latest_version"
    assert session.commands == []


def test_generate_config_uses_explicit_latest_version_topic(
    make_update: UpdateFactory,
):
    _, entity = make_update(latest_version_topic="custom/latest")

    assert entity.generate_config()["latest_version_topic"] == "custom/latest"


def test_generate_config_with_custom_payload_install(make_update: UpdateFactory):
    _, entity = make_update(payload_install="UPGRADE")
    assert entity.generate_config()["payload_install"] == "UPGRADE"


def test_set_installed_version_publishes_retained_state(
    update: tuple[RecordingSession, Update],
):
    session, entity = update
    asyncio.run(entity.set_installed_version("1.2.3"))

    published = published_payload(session.published[-1])
    assert published["installed_version"] == "1.2.3"
    assert published["in_progress"] is False
    assert session.published[-1].topic == entity.state_topic
    assert session.published[-1].retain is True


def test_set_latest_version_publishes_retained_topic(
    update: tuple[RecordingSession, Update],
):
    session, entity = update
    asyncio.run(entity.set_latest_version("1.2.4"))

    assert session.published[-1].topic == "hmd/update/test/latest_version"
    assert session.published[-1].payload == "1.2.4"
    assert session.published[-1].retain is True


def test_set_progress_valid(update: tuple[RecordingSession, Update]):
    session, entity = update
    asyncio.run(entity.set_progress(50))

    published = published_payload(session.published[-1])
    assert published["in_progress"] is True
    assert published["update_percentage"] == 50


def test_set_progress_invalid_range(update: tuple[RecordingSession, Update]):
    _, entity = update
    with pytest.raises(ValueError, match="Progress must be between 0 and 100"):
        asyncio.run(entity.set_progress(-1))
    with pytest.raises(ValueError, match="Progress must be between 0 and 100"):
        asyncio.run(entity.set_progress(101))


def test_set_state_with_metadata(update: tuple[RecordingSession, Update]):
    session, entity = update
    asyncio.run(
        entity.set_state(
            installed="1.0.0",
            latest="1.1.0",
            title="Major Update",
            release_summary="Bug fixes and new features",
            release_url="https://example.com/releases/1.1.0",
            entity_picture="https://example.com/icon.png",
            progress=50,
            in_progress=False,
        )
    )

    published = published_payload(session.published[-1])
    assert published["installed_version"] == "1.0.0"
    assert published["latest_version"] == "1.1.0"
    assert published["title"] == "Major Update"
    assert published["release_summary"] == "Bug fixes and new features"
    assert published["release_url"] == "https://example.com/releases/1.1.0"
    assert published["entity_picture"] == "https://example.com/icon.png"
    assert published["update_percentage"] == 50
    assert published["in_progress"] is True


def test_update_state_validation_rejects_invalid_payload(
    update: tuple[RecordingSession, Update],
):
    _, entity = update
    with pytest.raises(ValueError, match="Invalid update state payload"):
        asyncio.run(
            invoke_update_state(
                entity, {"installed_version": "1.0.0", "update_percentage": 150}
            )
        )
    with pytest.raises(ValueError, match="Invalid update state payload"):
        asyncio.run(
            invoke_update_state(
                entity, {"installed_version": "1.0.0", "release_url": "not-a-valid-url"}
            )
        )


def test_update_state_excludes_none_values(update: tuple[RecordingSession, Update]):
    session, entity = update
    asyncio.run(
        invoke_update_state(
            entity,
            {
                "installed_version": "1.0.0",
                "latest_version": None,
                "in_progress": False,
                "title": None,
            },
        )
    )

    published = published_payload(session.published[-1])
    assert "installed_version" in published
    assert "in_progress" in published
    assert "latest_version" not in published
    assert "title" not in published


def test_typeddict_validation_directly():
    from pydantic import HttpUrl

    from ha_mqtt_discoverable.sensors import update_state_validator

    valid_data: UpdateStatePayload = {
        "installed_version": "1.0.0",
        "latest_version": "1.1.0",
        "update_percentage": 50,
        "in_progress": True,
        "release_url": HttpUrl("https://example.com/release"),
    }

    validated = update_state_validator.validate_python(valid_data)
    assert validated.get("installed_version") == "1.0.0"
    assert validated.get("latest_version") == "1.1.0"
    assert validated.get("update_percentage") == 50
    assert validated.get("in_progress") is True
    assert str(validated.get("release_url")) == "https://example.com/release"


def test_typeddict_validation_invalid_values():
    from ha_mqtt_discoverable.sensors import update_state_validator

    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"update_percentage": 150})
    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"update_percentage": -10})
    with pytest.raises(ValidationError):
        update_state_validator.validate_python({"release_url": "not-a-url"})
