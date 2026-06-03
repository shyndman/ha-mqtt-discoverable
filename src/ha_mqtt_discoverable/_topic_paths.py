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

from ha_mqtt_discoverable._models import EntityInfo
from ha_mqtt_discoverable.utils import clean_string


def build_entity_topic_basename(entity: EntityInfo) -> str:
    return clean_string(
        entity.object_id if entity.object_id is not None else entity.name
    )


def build_entity_topic(entity: EntityInfo) -> str:
    entity_topic = entity.component
    if entity.device is not None:
        entity_topic += f"/{clean_string(entity.device.name)}"
    entity_topic += f"/{build_entity_topic_basename(entity)}"
    return entity_topic


def build_prefixed_topic(prefix: str, entity_topic: str, suffix: str) -> str:
    return f"{prefix}/{entity_topic}/{suffix}"


def build_config_topic(discovery_prefix: str, entity_topic: str) -> str:
    return build_prefixed_topic(discovery_prefix, entity_topic, "config")


def build_state_topic(
    state_prefix: str, entity_topic: str, suffix: str = "state"
) -> str:
    return build_prefixed_topic(state_prefix, entity_topic, suffix)


def build_command_topic(state_prefix: str, entity_topic: str) -> str:
    return build_state_topic(state_prefix, entity_topic, "command")


def build_status_topic(state_prefix: str, client_name: str) -> str:
    """Session-level status topic carrying the publisher's online/offline (LWT) state."""
    return f"{state_prefix}/{client_name}/status"
