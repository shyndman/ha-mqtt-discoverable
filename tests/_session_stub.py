from __future__ import annotations

from dataclasses import dataclass

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable._topic_paths import build_status_topic


@dataclass(slots=True)
class PublishedMessage:
    topic: str
    payload: str | bytes | int | float | None
    retain: bool
    qos: int


@dataclass(slots=True)
class RegisteredCommand:
    topic: str
    sender: object
    callback: object
    parser: object | None
    command_name: str | None
    qos: int


class RecordingSession:
    def __init__(self, settings: Settings.MQTT) -> None:
        self.settings: Settings.MQTT = settings
        self.published: list[PublishedMessage] = []
        self.commands: list[RegisteredCommand] = []
        self.failure: BaseException | None = None

    @property
    def discovery_prefix(self) -> str:
        return self.settings.discovery_prefix

    @property
    def state_prefix(self) -> str:
        return self.settings.state_prefix

    @property
    def status_topic(self) -> str:
        return build_status_topic(self.settings.state_prefix, self.settings.client_name)

    def _check_failure(self) -> None:
        if self.failure is not None:
            raise self.failure

    async def publish(
        self,
        topic: str,
        payload: str | bytes | int | float | None,
        *,
        retain: bool = False,
        qos: int = 0,
    ) -> None:
        self._check_failure()
        self.published.append(PublishedMessage(topic, payload, retain, qos))

    def subscribe(self, topic: str, callback: object, *, qos: int = 1) -> None:
        self._check_failure()
        self.commands.append(
            RegisteredCommand(
                topic=topic,
                sender=callback,
                callback=callback,
                parser=None,
                command_name=None,
                qos=qos,
            )
        )

    def register_command(
        self,
        topic: str,
        sender: object,
        callback: object,
        *,
        parser: object | None = None,
        command_name: str | None = None,
        qos: int = 1,
    ) -> None:
        self._check_failure()
        self.commands.append(
            RegisteredCommand(
                topic=topic,
                sender=sender,
                callback=callback,
                parser=parser,
                command_name=command_name,
                qos=qos,
            )
        )

    def poison(self, exc: BaseException) -> None:
        self.failure = exc
