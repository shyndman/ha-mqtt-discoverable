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
from threading import Event

import pytest
from paho.mqtt import publish
from paho.mqtt.client import Client, MQTTMessage

from ha_mqtt_discoverable import EntityInfo, Settings, Subscriber


def noop_command_callback(
    _client: Client, _user_data: object | None, _message: MQTTMessage
) -> None:
    pass


def command_topic(subscriber: Subscriber[EntityInfo]) -> str:
    topic = subscriber.generate_config()["command_topic"]
    assert isinstance(topic, str)
    return topic


@pytest.fixture
def subscriber() -> Subscriber[EntityInfo]:
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="button")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    # Define an empty `command_callback`
    return Subscriber(settings, noop_command_callback)


def test_required_config():
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="button")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    # Define empty callback
    sensor = Subscriber(settings, noop_command_callback)
    assert sensor is not None


def test_generate_config(subscriber: Subscriber[EntityInfo]):
    config = subscriber.generate_config()

    assert config is not None
    # Check that command topic is part of the output config
    assert config["command_topic"] == command_topic(subscriber)


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
    # Wait some seconds for the subscription to take effect
    time.sleep(2)

    # Send a command to the command topic
    publish.single(command_topic(switch), "on", hostname="localhost")

    assert message_received.wait(2)
