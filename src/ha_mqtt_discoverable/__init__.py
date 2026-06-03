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

from importlib import metadata
from typing import cast

from ha_mqtt_discoverable._base import Discoverable, Subscriber
from ha_mqtt_discoverable._config import CONFIGURATION_KEY_NAMES
from ha_mqtt_discoverable._models import (
    DeviceInfo,
    EntityInfo,
    EntityType,
    Settings,
    ValidatorValues,
)
from ha_mqtt_discoverable._session import (
    CommandCallback,
    CommandPayloadParser,
    MqttSession,
    ParsedCommandCallback,
)

__version__ = metadata.version(cast(str, __package__))

__all__ = [
    "CONFIGURATION_KEY_NAMES",
    "CommandCallback",
    "CommandPayloadParser",
    "DeviceInfo",
    "Discoverable",
    "EntityInfo",
    "EntityType",
    "MqttSession",
    "ParsedCommandCallback",
    "Settings",
    "Subscriber",
    "ValidatorValues",
    "__version__",
]
