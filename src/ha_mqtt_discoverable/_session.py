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

import asyncio
import ssl
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self, cast, overload, runtime_checkable

import aiomqtt
import paho.mqtt.client as mqtt

from ha_mqtt_discoverable._logging import get_logger
from ha_mqtt_discoverable._models import EntityInfo, Settings
from ha_mqtt_discoverable._topic_paths import build_status_topic

logger = get_logger(__name__)


type PublishPayload = str | bytes | int | float | None

type SubscriptionCallback = Callable[[aiomqtt.Message], Awaitable[None]]
type CallbackErrorHandler = Callable[[Exception, aiomqtt.Message], Awaitable[None]]
type CommandCallback[SenderT] = Callable[[SenderT, aiomqtt.Message], Awaitable[None]]
type ParsedCommandCallback[SenderT, ParsedT] = Callable[
    [SenderT, ParsedT, aiomqtt.Message], Awaitable[None]
]
type CommandPayloadParser[ParsedT] = Callable[[aiomqtt.Message], ParsedT]


class SessionLike(Protocol):
    @property
    def discovery_prefix(self) -> str: ...

    @property
    def state_prefix(self) -> str: ...

    @property
    def status_topic(self) -> str: ...

    async def publish(
        self,
        topic: str,
        payload: PublishPayload,
        *,
        retain: bool = False,
        qos: int = 0,
    ) -> None: ...

    @overload
    def register_command[SenderT](
        self,
        topic: str,
        sender: SenderT,
        callback: CommandCallback[SenderT],
        *,
        qos: int = 1,
        command_name: str | None = None,
    ) -> None: ...

    @overload
    def register_command[SenderT, ParsedT](
        self,
        topic: str,
        sender: SenderT,
        callback: ParsedCommandCallback[SenderT, ParsedT],
        *,
        parser: CommandPayloadParser[ParsedT],
        qos: int = 1,
        command_name: str | None = None,
    ) -> None: ...


@runtime_checkable
class _EntityBackedSender(Protocol):
    @property
    def entity(self) -> EntityInfo: ...


@dataclass(frozen=True)
class _Subscription:
    topic: str
    qos: int
    callback: SubscriptionCallback


class MqttSession:
    _settings: Settings.MQTT
    _client: aiomqtt.Client | None
    _listener_task: asyncio.Task[None] | None
    _subscription_tasks: set[asyncio.Task[object]]
    _subscriptions: dict[str, _Subscription]
    _failure: Exception | None
    _on_callback_error: CallbackErrorHandler | None

    def __init__(
        self,
        settings: Settings.MQTT,
        *,
        on_callback_error: CallbackErrorHandler | None = None,
    ) -> None:
        self._settings = settings
        self._client = None
        self._listener_task = None
        self._subscription_tasks = set()
        self._subscriptions = {}
        self._failure = None
        self._on_callback_error = on_callback_error

    @property
    def client(self) -> aiomqtt.Client:
        client = self._client
        if client is None:
            raise RuntimeError("MQTT session is not connected")
        return client

    @property
    def settings(self) -> Settings.MQTT:
        return self._settings

    @property
    def discovery_prefix(self) -> str:
        return self._settings.discovery_prefix

    @property
    def state_prefix(self) -> str:
        return self._settings.state_prefix

    @property
    def status_topic(self) -> str:
        return build_status_topic(
            self._settings.state_prefix, self._settings.client_name
        )

    async def __aenter__(self) -> Self:
        self._raise_if_poisoned()
        if self._client is not None:
            raise RuntimeError("MQTT session is already connected")

        host = self._settings.host
        port = self._settings.port
        logger.info("connecting to mqtt", host=host, port=port)
        client = aiomqtt.Client(
            host,
            port=port,
            username=self._settings.username,
            password=self._settings.password,
            identifier=self._settings.client_name,
            tls_params=self._build_tls_params(),
            will=aiomqtt.Will(
                topic=self.status_topic,
                payload="offline",
                qos=1,
                retain=True,
            ),
        )
        self._client = client

        try:
            await client.__aenter__()
            await self._subscribe_all_registered_topics()
            self._listener_task = asyncio.create_task(self._listen())
            await client.publish(self.status_topic, "online", retain=True, qos=1)
        except Exception:
            try:
                await client.__aexit__(None, None, None)
            except Exception:
                pass
            self._client = None
            raise

        logger.info("connected to mqtt", host=host, port=port)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        listener_task = self._listener_task
        self._listener_task = None
        client = self._client
        self._client = None
        exit_error: Exception | None = None

        try:
            await self._await_subscription_tasks()
        except Exception as error:
            self._store_failure(error)
            exit_error = error

        if listener_task is not None:
            if not listener_task.done():
                listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
            except Exception as error:
                self._store_failure(error)
                if exit_error is None:
                    exit_error = error
        if client is not None:
            try:
                await client.publish(self.status_topic, "offline", retain=True, qos=1)
            except Exception as error:
                self._store_failure(error)
                if exit_error is None:
                    exit_error = error
            logger.info(
                "disconnecting from mqtt",
                host=self._settings.host,
                port=self._settings.port,
            )
            try:
                await client.__aexit__(exc_type, exc, tb)
            except Exception as error:
                self._store_failure(error)
                if exit_error is None:
                    exit_error = error

        if exc is None:
            if exit_error is not None:
                raise RuntimeError("MQTT session is poisoned") from exit_error
            self._raise_if_poisoned()

    async def publish(
        self,
        topic: str,
        payload: PublishPayload,
        *,
        retain: bool = False,
        qos: int = 0,
    ) -> None:
        self._raise_if_poisoned()
        await self._await_subscription_tasks()
        self._raise_if_poisoned()
        await self.client.publish(topic, payload=payload, retain=retain, qos=qos)

    def subscribe(
        self,
        topic: str,
        callback: SubscriptionCallback,
        *,
        qos: int = 1,
    ) -> None:
        self._register_subscription(
            _Subscription(topic=topic, qos=qos, callback=callback)
        )

    @overload
    def register_command[SenderT](
        self,
        topic: str,
        sender: SenderT,
        callback: CommandCallback[SenderT],
        *,
        qos: int = 1,
        command_name: str | None = None,
    ) -> None: ...

    @overload
    def register_command[SenderT, ParsedT](
        self,
        topic: str,
        sender: SenderT,
        callback: ParsedCommandCallback[SenderT, ParsedT],
        *,
        parser: CommandPayloadParser[ParsedT],
        qos: int = 1,
        command_name: str | None = None,
    ) -> None: ...

    def register_command[SenderT, ParsedT](
        self,
        topic: str,
        sender: SenderT,
        callback: CommandCallback[SenderT] | ParsedCommandCallback[SenderT, ParsedT],
        *,
        parser: CommandPayloadParser[ParsedT] | None = None,
        qos: int = 1,
        command_name: str | None = None,
    ) -> None:
        entity, component = _sender_identity(sender)
        log_context: dict[str, object] = {
            "entity": entity,
            "component": component,
            "command": command_name or "command",
            "topic": topic,
        }
        dispatch = cast(Callable[..., Awaitable[None]], callback)

        async def handle(message: aiomqtt.Message) -> None:
            if parser is not None:
                try:
                    parsed_value = parser(message)
                except (UnicodeDecodeError, ValueError, TypeError) as error:
                    logger.warning(
                        "failed to parse command payload",
                        **log_context,
                        payload=message.payload.decode(errors="replace"),
                        error=str(error),
                    )
                    return
                args: tuple[object, ...] = (sender, parsed_value, message)
            else:
                args = (sender, message)

            logger.debug("dispatching command", **log_context)
            try:
                await dispatch(*args)
            except Exception:
                logger.exception("command callback failed", **log_context)
                raise

        self._register_subscription(
            _Subscription(topic=topic, qos=qos, callback=handle)
        )
        logger.info("registered command callback", **log_context)

    def _build_tls_params(self) -> aiomqtt.TLSParameters | None:
        if not (
            self._settings.use_tls
            or self._settings.tls_ca_cert is not None
            or self._settings.tls_certfile is not None
            or self._settings.tls_key is not None
        ):
            return None

        return aiomqtt.TLSParameters(
            ca_certs=self._settings.tls_ca_cert,
            certfile=self._settings.tls_certfile,
            keyfile=self._settings.tls_key,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS,
        )

    def _register_subscription(self, subscription: _Subscription) -> None:
        self._raise_if_poisoned()
        existing = self._subscriptions.get(subscription.topic)
        if existing is not None:
            raise RuntimeError(
                f"A subscription is already registered for topic '{subscription.topic}'"
            )

        self._subscriptions[subscription.topic] = subscription
        if self._client is not None:
            self._track_subscription_task(
                asyncio.create_task(
                    self.client.subscribe(subscription.topic, qos=subscription.qos)
                )
            )

    async def _subscribe_all_registered_topics(self) -> None:
        await asyncio.gather(
            *(
                self.client.subscribe(subscription.topic, qos=subscription.qos)
                for subscription in self._subscriptions.values()
            )
        )

    async def _listen(self) -> None:
        try:
            async for message in self.client.messages:
                topic = str(message.topic)
                logger.debug(
                    "received mqtt message",
                    topic=topic,
                    retain=message.retain,
                    qos=message.qos,
                )
                # Match by MQTT topic filter rather than exact string so that
                # wildcard subscriptions ('+'/'#') receive messages. Overlapping
                # filters are valid MQTT, so dispatch to every match. Snapshot
                # the subscriptions because a callback may register more.
                dispatched = False
                for subscription in tuple(self._subscriptions.values()):
                    if mqtt.topic_matches_sub(subscription.topic, topic):
                        dispatched = True
                        await self._dispatch(subscription, message)
                if not dispatched:
                    logger.debug("no subscription matched message", topic=topic)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._store_failure(error)
            raise

    async def _dispatch(
        self, subscription: _Subscription, message: aiomqtt.Message
    ) -> None:
        try:
            await subscription.callback(message)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            # A callback raised while handling a delivered message. This is a
            # runtime, per-message event -- the session, connection, and
            # subscription are all still healthy -- so it is treated separately
            # from a failure to *establish* a subscription (see
            # _track_subscription_task). If the application provided an error
            # handler it gets a chance to deal with it; returning cleanly means
            # the failure is handled and the listener keeps serving every other
            # entity. With no handler (or if the handler itself raises) we fall
            # through to poison the session and fail loud.
            if self._on_callback_error is None:
                raise
            await self._on_callback_error(error, message)

    async def _await_subscription_tasks(self) -> None:
        # Re-loop because new subscriptions can be registered (adding tasks)
        # while we are awaiting the current snapshot.
        while self._subscription_tasks:
            pending = tuple(self._subscription_tasks)
            await asyncio.gather(*pending)

    def _track_subscription_task(self, task: asyncio.Task[object]) -> None:
        self._subscription_tasks.add(task)

        def cleanup(completed: asyncio.Task[object]) -> None:
            self._subscription_tasks.discard(completed)
            if completed.cancelled():
                return
            error = completed.exception()
            if isinstance(error, Exception):
                # A subscribe runs as a detached task because it is started
                # from a synchronous caller (entity constructors), so its
                # failure (local error or a rejected broker SUBACK) cannot be
                # raised to that caller. By design we poison the whole session
                # rather than let one entity silently lose its subscription:
                # the next session operation re-raises this, failing loudly.
                # This is intentionally all-or-nothing -- we do not support
                # continuing with partial functionality.
                self._store_failure(error)

        task.add_done_callback(cleanup)

    def _store_failure(self, error: Exception) -> None:
        if self._failure is None:
            self._failure = error

    def _raise_if_poisoned(self) -> None:
        if self._failure is not None:
            raise self._failure


def _sender_identity(sender: object) -> tuple[str | None, str | None]:
    if not isinstance(sender, _EntityBackedSender):
        return None, None
    entity = sender.entity
    return (entity.name, entity.component)
