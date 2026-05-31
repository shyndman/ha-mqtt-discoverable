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
import asyncio
from collections.abc import Iterator
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import cast, override

import pytest
import paho.mqtt.client as mqtt
from paho.mqtt.client import Client, ConnectFlags, MQTTMessage, MQTTv5
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.subscribeoptions import SubscribeOptions

from ha_mqtt_discoverable import DeviceInfo, Discoverable, EntityInfo, Settings


class DiscoverableHarness(Discoverable[EntityInfo]):
    def connect_client(self) -> None:
        self._connect_client()

    def setup_client(self) -> None:
        self._setup_client()

    def publish_state(self, value: str | float | int | None) -> None:
        _ = self._state_helper(value)

    def set_device_info(self, device: DeviceInfo, unique_id: str) -> None:
        self._entity.device = device
        self._entity.unique_id = unique_id


class TrackingClient(Client):
    disconnect_called: bool
    loop_stop_called: bool

    def __init__(self) -> None:
        super().__init__(callback_api_version=CallbackAPIVersion.VERSION2)
        self.disconnect_called = False
        self.loop_stop_called = False

    @override
    def disconnect(
        self,
        reasoncode: ReasonCode | None = None,
        properties: Properties | None = None,
    ) -> MQTTErrorCode:
        self.disconnect_called = True
        return super().disconnect(reasoncode=reasoncode, properties=properties)

    @override
    def loop_stop(self) -> MQTTErrorCode:
        self.loop_stop_called = True
        return super().loop_stop()


class InlineTrackingClient(TrackingClient):
    connect_called: int
    disconnect_called: bool
    disconnect_call_count: int
    loop_start_called: int
    loop_stop_called: bool
    loop_stop_call_count: int

    def __init__(self) -> None:
        super().__init__()
        self.connect_called = 0
        self.disconnect_call_count = 0
        self.loop_start_called = 0
        self.loop_stop_call_count = 0

    @override
    def connect(self, *args: object, **kwargs: object) -> MQTTErrorCode:
        self.connect_called += 1
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    @override
    def disconnect(
        self,
        reasoncode: ReasonCode | None = None,
        properties: Properties | None = None,
    ) -> MQTTErrorCode:
        self.disconnect_call_count += 1
        self.disconnect_called = True
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    @override
    def loop_start(self) -> MQTTErrorCode:
        self.loop_start_called += 1
        return MQTTErrorCode.MQTT_ERR_SUCCESS

    @override
    def loop_stop(self) -> MQTTErrorCode:
        self.loop_stop_call_count += 1
        self.loop_stop_called = True
        return MQTTErrorCode.MQTT_ERR_SUCCESS


@pytest.fixture
def discoverable() -> Iterator[DiscoverableHarness]:
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="binary_sensor")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    instance = DiscoverableHarness(settings)
    yield instance
    instance.close()


@pytest.fixture
def discoverable_availability() -> Iterator[DiscoverableHarness]:
    """Return an instance of Discoverable configured with `manual_availability`"""
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="binary_sensor")
    settings = Settings(
        mqtt=mqtt_settings, entity=sensor_info, manual_availability=True
    )
    instance = DiscoverableHarness(settings)
    yield instance
    instance.close()


def test_required_config():
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="binary_sensor")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    d = Discoverable(settings)
    try:
        assert d is not None
    finally:
        d.close()


def test_missing_config():
    sensor_info = EntityInfo(name="test", component="binary_sensor")
    # Missing MQTT settings
    with pytest.raises(ValueError):
        Settings[EntityInfo].model_validate({"entity": sensor_info.model_dump()})


def test_custom_on_connect():
    """Test that the custom callback function is invoked when we connect to MQTT"""
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="binary_sensor")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)

    is_connected = Event()

    def custom_callback(
        _client: Client,
        _user_data: object,
        _flags: ConnectFlags,
        _reason_code: ReasonCode,
        _properties: Properties | None,
    ) -> None:
        is_connected.set()

    d = DiscoverableHarness(settings, custom_callback)
    try:
        d.connect_client()
        assert is_connected.wait(5)
    finally:
        d.close()


def test_custom_on_connect_must_be_called(monkeypatch: pytest.MonkeyPatch):
    """Test that _on_connect must be called if there is a custom_callback"""
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="binary_sensor")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    connect_called = False

    def fake_connect_client(_self: Discoverable[EntityInfo]) -> None:
        nonlocal connect_called
        connect_called = True

    monkeypatch.setattr(Discoverable, "_connect_client", fake_connect_client)

    def custom_callback(
        _client: Client,
        _user_data: object,
        _flags: ConnectFlags,
        _reason_code: ReasonCode,
        _properties: Properties | None,
    ) -> None:
        return None

    Discoverable(settings, custom_callback)
    assert connect_called is False


def test_mqtt_topics():
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="test", component="binary_sensor")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    d = Discoverable[EntityInfo](settings)
    try:
        assert d.config_topic == "homeassistant/binary_sensor/test/config"
        assert d.state_topic == "hmd/binary_sensor/test/state"
        assert d.attributes_topic == "hmd/binary_sensor/test/attributes"
    finally:
        d.close()


def test_mqtt_topics_with_device():
    mqtt_settings = Settings.MQTT(host="localhost")
    device = DeviceInfo(name="test_device", identifiers="id")
    sensor_info = EntityInfo(
        name="test", component="binary_sensor", device=device, unique_id="unique_id"
    )
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    d = Discoverable[EntityInfo](settings)
    try:
        assert d.config_topic == "homeassistant/binary_sensor/test_device/test/config"
        assert d.state_topic == "hmd/binary_sensor/test_device/test/state"
        assert d.attributes_topic == "hmd/binary_sensor/test_device/test/attributes"
    finally:
        d.close()


def test_generate_config(discoverable: DiscoverableHarness):
    device_config = discoverable.generate_config()

    assert device_config is not None
    assert device_config["name"] == "test"
    assert device_config["component"] == "binary_sensor"
    assert device_config["state_topic"] == "hmd/binary_sensor/test/state"
    assert device_config["json_attributes_topic"] == "hmd/binary_sensor/test/attributes"


def test_setup_client(discoverable: DiscoverableHarness):
    # Try to setup client
    discoverable.setup_client()
    # Check that we save the client
    assert discoverable.mqtt_client is not None


def test_connect_client(discoverable: DiscoverableHarness):
    # Try to connect to MQTT
    discoverable.setup_client()
    discoverable.connect_client()
    # Check that we save the client
    assert discoverable.mqtt_client is not None


def test_write_config(discoverable: DiscoverableHarness):
    # Write config to MQTT
    discoverable.write_config()

    assert discoverable.wrote_configuration is True
    assert discoverable.config_message is not None


def test_state_helper(discoverable: DiscoverableHarness):
    # Write a state to MQTT
    discoverable.publish_state("test")
    # Check that flag is set
    assert discoverable.wrote_configuration is True
    assert discoverable.config_message is not None


def test_device_info(discoverable: DiscoverableHarness):
    device_info = DeviceInfo(name="Test device", identifiers="test_device_id")
    discoverable.set_device_info(device_info, "test_sensor")
    config = discoverable.generate_config()

    # Check that the device info is put in the output config
    assert config["device"] is not None
    device_config = cast(dict[str, object], config["device"])
    assert device_config["name"] == "Test device"

    discoverable.write_config()


def test_device_missing_unique_id():
    device_info = DeviceInfo(name="Test device", identifiers="test_device_id")
    with pytest.raises(ValueError):
        EntityInfo(name="test", component="binary_sensor", device=device_info)


def test_device_without_identifiers():
    # Identifiers or connections is required
    with pytest.raises(ValueError):
        DeviceInfo(name="Test device")


def test_device_with_unique_id():
    device_info = DeviceInfo(name="Test device", identifiers="test_device_id")
    EntityInfo(
        name="test", component="binary_sensor", unique_id="id", device=device_info
    )


def test_name_with_space():
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(name="Name with space", component="binary_sensor")
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    d = Discoverable[EntityInfo](settings)
    try:
        d.write_config()
    finally:
        d.close()


def test_custom_object_id():
    mqtt_settings = Settings.MQTT(host="localhost")
    sensor_info = EntityInfo(
        name="Test name", component="binary_sensor", object_id="custom object id"
    )
    settings = Settings(mqtt=mqtt_settings, entity=sensor_info)
    d = Discoverable[EntityInfo](settings)
    try:
        d.write_config()
    finally:
        d.close()


def test_str(discoverable: DiscoverableHarness):
    string = str(discoverable)
    print(string)
    assert "settings" in string


# Define a callback function to be invoked when we receive a message on the topic
def message_callback(
    client: Client,
    userdata: Event | None,
    message: MQTTMessage,
) -> None:
    logging.info("Received %s", message)
    # If the broker is `dirty` and contains messages send by other test functions,
    # skip these retained messages
    if message.retain:
        logging.warning("Skipping retained message")
        return
    payload = message.payload.decode()
    assert "test" in payload
    assert userdata is not None
    userdata.set()
    client.disconnect()


def test_publish_multithread(discoverable: DiscoverableHarness):
    received_message = Event()
    mqtt_client = Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        protocol=MQTTv5,
        userdata=received_message,
    )

    mqtt_client.connect(host="localhost")
    mqtt_client.on_message = message_callback
    mqtt_client.subscribe(
        (
            "hmd/binary_sensor/test/state/#",
            SubscribeOptions(retainHandling=SubscribeOptions.RETAIN_DO_NOT_SEND),
        )
    )
    mqtt_client.loop_start()

    # Write a state to MQTT from another thread
    with ThreadPoolExecutor() as executor:
        future = executor.submit(discoverable.publish_state, "test")
        # Wait for executor to finish
        future.result(1)
        # Check that flag is set
        assert discoverable.wrote_configuration is True
        assert discoverable.config_message is not None

    # Wait until we receive the published message
    assert received_message.wait(1)


def test_publish_async(discoverable: DiscoverableHarness):
    received_message = Event()
    mqtt_client = Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        protocol=MQTTv5,
        userdata=received_message,
    )

    mqtt_client.connect(host="localhost", clean_start=True)
    mqtt_client.on_message = message_callback
    mqtt_client.subscribe(
        (
            "hmd/binary_sensor/test/state/#",
            SubscribeOptions(retainHandling=SubscribeOptions.RETAIN_DO_NOT_SEND),
        )
    )
    mqtt_client.loop_start()

    # Write a state to MQTT from an asyncio event loop
    async def publish_state() -> None:
        discoverable.publish_state("test")

    asyncio.run(publish_state())

    # Wait until we receive the published message
    assert received_message.wait(1)


def test_close_owned_client_is_idempotent(monkeypatch: pytest.MonkeyPatch):
    tracking_client = InlineTrackingClient()
    sensor_info = EntityInfo(name="test", component="binary_sensor")
    settings = Settings(mqtt=Settings.MQTT(host="localhost"), entity=sensor_info)

    def client_factory(*_args: object, **_kwargs: object) -> InlineTrackingClient:
        return tracking_client

    monkeypatch.setattr(mqtt, "Client", client_factory)

    discoverable = DiscoverableHarness(settings)

    discoverable.close()
    discoverable.close()

    assert tracking_client.connect_called == 1
    assert tracking_client.disconnect_call_count == 1
    assert tracking_client.loop_start_called == 1
    assert tracking_client.loop_stop_call_count == 1


def test_close_skips_injected_client():
    tracking_client = TrackingClient()
    sensor_info = EntityInfo(name="test", component="binary_sensor")
    settings = Settings(
        mqtt=Settings.MQTT(host="localhost", client=tracking_client),
        entity=sensor_info,
    )

    discoverable = Discoverable[EntityInfo](settings)
    discoverable.close()
    discoverable.close()

    assert tracking_client.disconnect_called is False
    assert tracking_client.loop_stop_called is False


def test_set_availability_topic(
    discoverable_availability: Discoverable[EntityInfo],
):
    assert discoverable_availability.availability_topic is not None
    assert (
        discoverable_availability.availability_topic
        == "hmd/binary_sensor/test/availability"
    )


def test_config_availability_topic(
    discoverable_availability: Discoverable[EntityInfo],
):
    config = discoverable_availability.generate_config()
    assert config.get("availability_topic") is not None


def test_set_availability(
    discoverable_availability: DiscoverableHarness,
):
    received_payloads: list[str] = []
    availability_received = Event()

    def availability_callback(
        _client: Client,
        _user_data: object,
        message: MQTTMessage,
    ) -> None:
        if message.retain:
            return

        received_payloads.append(message.payload.decode("utf-8"))
        if len(received_payloads) == 2:
            availability_received.set()

    mqtt_client = Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        protocol=MQTTv5,
    )
    mqtt_client.connect(host="localhost", clean_start=True)
    mqtt_client.on_message = availability_callback
    mqtt_client.subscribe(
        (
            discoverable_availability.availability_topic,
            SubscribeOptions(retainHandling=SubscribeOptions.RETAIN_DO_NOT_SEND),
        )
    )
    mqtt_client.loop_start()

    discoverable_availability.set_availability(True)
    discoverable_availability.set_availability(False)

    assert availability_received.wait(1)
    assert received_payloads == ["online", "offline"]
    mqtt_client.disconnect()
    mqtt_client.loop_stop()


def test_set_availability_wrong_config(discoverable: DiscoverableHarness):
    """A discoverable that has not set availability to manual cannot invoke the \
        methods"""
    with pytest.raises(RuntimeError):
        discoverable.set_availability(True)


def test_set_attributes(discoverable: DiscoverableHarness):
    attributes: dict[str, object] = {"test attribute": "test"}
    discoverable.set_attributes(attributes)
