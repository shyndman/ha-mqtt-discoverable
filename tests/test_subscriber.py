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
import logging
import time
from collections.abc import Iterator
from threading import Event
from typing import Callable, cast, override

import pytest
from paho.mqtt import publish
import paho.mqtt.client as mqtt
from paho.mqtt.client import Client, MQTTMessage
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.subscribeoptions import SubscribeOptions

from ha_mqtt_discoverable import EntityInfo, Settings, Subscriber


def noop_command_callback(
    _client: Client, _user_data: object | None, _message: MQTTMessage
) -> None:
    pass


def command_topic(subscriber: Subscriber[EntityInfo]) -> str:
    topic = subscriber.generate_config()["command_topic"]
    assert isinstance(topic, str)
    return topic


class InlineSubscriberClient(Client):
    subscribed_topic: str | None

    def __init__(self) -> None:
        super().__init__(callback_api_version=CallbackAPIVersion.VERSION2)
        self.subscribed_topic = None

    @override
    def connect(self, *args: object, **kwargs: object) -> MQTTErrorCode:
        if self.on_connect is not None:
            callback = cast(Callable[..., object], self.on_connect)
            _ = callback(self, None, {}, 0, None)
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    @override
    def loop_start(self) -> MQTTErrorCode:
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    @override
    def disconnect(
        self,
        reasoncode: ReasonCode | None = None,
        properties: Properties | None = None,
    ) -> MQTTErrorCode:
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    @override
    def loop_stop(self) -> MQTTErrorCode:
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    @override
    def subscribe(
        self,
        topic: str
        | tuple[str, int]
        | tuple[str, SubscribeOptions]
        | list[tuple[str, int]]
        | list[tuple[str, SubscribeOptions]],
        qos: int = 0,
        options: SubscribeOptions | None = None,
        properties: Properties | None = None,
    ) -> tuple[MQTTErrorCode, int]:
        if isinstance(topic, str):
            self.subscribed_topic = topic
        elif isinstance(topic, tuple):
            self.subscribed_topic = topic[0]
        elif topic:
            self.subscribed_topic = topic[0][0]
        return (MQTTErrorCode.MQTT_ERR_SUCCESS, 1)


@pytest.fixture
def subscriber() -> Iterator[Subscriber[EntityInfo]]:
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="button")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    # Define an empty `command_callback`
    instance = Subscriber(settings, noop_command_callback)
    yield instance
    instance.close()


def test_required_config():
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="button")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    # Define empty callback
    sensor = Subscriber(settings, noop_command_callback)
    try:
        assert sensor is not None
    finally:
        sensor.close()


def test_generate_config(subscriber: Subscriber[EntityInfo]):
    config = subscriber.generate_config()

    assert config is not None
    # Check that command topic is part of the output config
    assert config["command_topic"] == command_topic(subscriber)


def test_subscriber_subscribes_to_command_topic_on_connect(
    monkeypatch: pytest.MonkeyPatch,
):
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test button", component="button")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    tracking_client = InlineSubscriberClient()

    def client_factory(*_args: object, **_kwargs: object) -> InlineSubscriberClient:
        return tracking_client

    monkeypatch.setattr(
        mqtt,
        "Client",
        client_factory,
    )

    subscriber = Subscriber(settings, noop_command_callback)
    try:
        assert tracking_client.subscribed_topic == command_topic(subscriber)
    finally:
        subscriber.close()


def test_command_callback():
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="switch")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)

    # Flag that waits for the command to be received
    message_received = Event()

    custom_user_data = "data"

    # Callback to receive the command message
    def custom_callback(
        _client: Client, user_data: str | None, message: MQTTMessage
    ) -> None:
        payload = message.payload.decode()
        logging.info(f"Received {payload}")
        assert payload == "on"
        assert user_data == custom_user_data
        message_received.set()

    switch = Subscriber(settings, custom_callback, custom_user_data)
    try:
        # Wait some seconds for the subscription to take effect
        time.sleep(2)

        # Send a command to the command topic
        publish.single(command_topic(switch), "on", hostname="localhost")

        assert message_received.wait(2)
    finally:
        switch.close()
