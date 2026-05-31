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
# Required to define a class itself as type https://stackoverflow.com/a/33533514
from __future__ import annotations

from ha_mqtt_discoverable._command_entities import (
    Button,
    ButtonInfo,
    Cover,
    CoverInfo,
    Light,
    LightInfo,
    Number,
    NumberInfo,
    Select,
    SelectInfo,
    Switch,
    SwitchInfo,
    Text,
    TextInfo,
)
from ha_mqtt_discoverable._device_entities import (
    Camera,
    CameraInfo,
    DeviceTrigger,
    DeviceTriggerInfo,
    Image,
    ImageInfo,
)
from ha_mqtt_discoverable._sensor_entities import (
    BinarySensor,
    BinarySensorInfo,
    Sensor,
    SensorInfo,
)
from ha_mqtt_discoverable._update import (
    Update,
    UpdateInfo,
    UpdateStatePayload,
    update_state_validator,
)

__all__ = [
    "BinarySensor",
    "BinarySensorInfo",
    "Button",
    "ButtonInfo",
    "Camera",
    "CameraInfo",
    "Cover",
    "CoverInfo",
    "DeviceTrigger",
    "DeviceTriggerInfo",
    "Image",
    "ImageInfo",
    "Light",
    "LightInfo",
    "Number",
    "NumberInfo",
    "Select",
    "SelectInfo",
    "Sensor",
    "SensorInfo",
    "Switch",
    "SwitchInfo",
    "Text",
    "TextInfo",
    "Update",
    "UpdateInfo",
    "UpdateStatePayload",
    "update_state_validator",
]
