import asyncio

import pytest

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Image, ImageInfo
from ._session_stub import RecordingSession


IMAGE_URL_TOPIC = "topic_to_publish_url_to"


@pytest.fixture
def image_info() -> ImageInfo:
    return ImageInfo(name="test", url_topic=IMAGE_URL_TOPIC)


@pytest.fixture
def image(image_info: ImageInfo) -> Image:
    session = RecordingSession(Settings.MQTT(host="localhost", client_name="test"))
    return Image(session, image_info)


def test_required_config(image: Image):
    assert image is not None


def test_generate_config(image: Image, image_info: ImageInfo):
    config = image.generate_config()
    assert config["url_topic"] == image_info.url_topic


def test_set_url() -> None:
    session = RecordingSession(Settings.MQTT(host="localhost", client_name="test"))
    entity = Image(session, ImageInfo(name="test", url_topic=IMAGE_URL_TOPIC))

    asyncio.run(entity.set_url("http://camera.local/latest.jpg"))

    by_topic = {message.topic: message for message in session.published}
    assert by_topic[entity.config_topic].retain is True
    assert by_topic[IMAGE_URL_TOPIC].payload == "http://camera.local/latest.jpg"
    assert by_topic[IMAGE_URL_TOPIC].retain is True
