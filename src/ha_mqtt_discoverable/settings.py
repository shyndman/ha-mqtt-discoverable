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

import logging
from typing import Protocol, cast

from ha_mqtt_discoverable.utils import read_yaml_file

logger = logging.getLogger(__name__)

type SettingsValue = object
type SettingsDict = dict[str, SettingsValue]


class _BaseCLISettings(Protocol):
    debug: bool
    client_name: str | None
    device_class: str | None
    device_id: str | None
    device_name: str | None
    mqtt_password: str | None
    mqtt_prefix: str | None
    mqtt_server: str | None
    mqtt_port: int | None
    mqtt_user: str | None
    use_tls: bool
    tls_certfile: str | None
    tls_key: str | None
    tls_ca_cert: str | None


class _BinarySensorCLISettings(_BaseCLISettings, Protocol):
    state: object
    metric_name: object


def _read_settings(path: str | None) -> SettingsDict:
    if path is None:
        return {}

    try:
        return read_yaml_file(path=path)
    except TypeError:
        return {}


def _set_optional_setting(
    settings: SettingsDict, *, key: str, cli: object, attr_name: str
) -> None:
    if hasattr(cli, attr_name):
        settings[key] = cast(object, getattr(cli, attr_name))


def load_mqtt_settings(path: str | None = None, cli: object = None) -> SettingsDict:
    """
    Base settings loader & validator

    Valid characters for object_id and node_id are [a-zA-Z0-9_-]
    """
    settings = _read_settings(path)
    cli_settings = cast(_BaseCLISettings, cli)

    settings["debug"] = cli_settings.debug
    # CLI args override stuff in the settings file

    # These are mandatory
    settings["client_name"] = cli_settings.client_name
    settings["device_class"] = cli_settings.device_class
    settings["device_id"] = cli_settings.device_id
    settings["device_name"] = cli_settings.device_name
    settings["mqtt_password"] = cli_settings.mqtt_password
    settings["mqtt_prefix"] = cli_settings.mqtt_prefix
    settings["mqtt_server"] = cli_settings.mqtt_server
    settings["mqtt_port"] = cli_settings.mqtt_port
    settings["mqtt_user"] = cli_settings.mqtt_user

    # Optional settings - make sure we don't raise an exception if they're unset
    _set_optional_setting(settings, key="model", cli=cli, attr_name="model")
    _set_optional_setting(settings, key="icon", cli=cli, attr_name="icon")
    _set_optional_setting(settings, key="unique_id", cli=cli, attr_name="unique_id")

    # ssl
    settings["use_tls"] = cli_settings.use_tls
    if cli_settings.use_tls:
        settings["certfile"] = cli_settings.tls_certfile
        settings["keyfile"] = cli_settings.tls_key
        settings["ca_certs"] = cli_settings.tls_ca_cert

    # TODO: refactor code, remove ignore
    # jscpd:ignore-start
    # Validate that we have all the settings data we need
    if "client_name" not in settings:
        raise RuntimeError("No client_name was specified")
    if "device_class" not in settings:
        raise RuntimeError("No device_class was specified")
    if "device_id" not in settings:
        raise RuntimeError("No device_id was specified")
    if "device_name" not in settings:
        raise RuntimeError("No device_name was specified")
    if "mqtt_prefix" not in settings:
        raise RuntimeError("You need to specify an mqtt prefix")
    if "mqtt_port" not in settings:
        raise RuntimeError("You need to specify an mqtt port")
    if "mqtt_user" not in settings:
        raise RuntimeError("No mqtt_user was specified")
    if "mqtt_password" not in settings:
        raise RuntimeError("No mqtt_password was specified")
    # jscpd:ignore-end

    return settings


def sensor_delete_settings(path: str | None = None, cli: object = None) -> SettingsDict:
    """
    Load settings
    Valid characters for object_id and node_id are [a-zA-Z0-9_-]
    """
    settings = _read_settings(path)
    cli_settings = cast(_BaseCLISettings, cli)

    # CLI args override stuff in the settings file
    if cli_settings.client_name:
        settings["client_name"] = cli_settings.client_name
    if cli_settings.device_id:
        settings["device_id"] = cli_settings.device_id
    if cli_settings.device_name:
        settings["device_name"] = cli_settings.device_name
    if cli_settings.mqtt_password:
        settings["mqtt_password"] = cli_settings.mqtt_password
    if cli_settings.mqtt_prefix:
        settings["mqtt_prefix"] = cli_settings.mqtt_prefix
    if cli_settings.mqtt_server:
        settings["mqtt_server"] = cli_settings.mqtt_server
    if cli_settings.mqtt_port:
        settings["mqtt_port"] = cli_settings.mqtt_port
    if cli_settings.mqtt_user:
        settings["mqtt_user"] = cli_settings.mqtt_user

    # Validate that we have all the settings data we need
    if "client_name" not in settings:
        raise RuntimeError("No client_name was specified")
    if "device_id" not in settings:
        raise RuntimeError("No device_id was specified")
    if "device_name" not in settings:
        raise RuntimeError("No device_name was specified")
    if "mqtt_prefix" not in settings:
        raise RuntimeError("You need to specify an mqtt prefix")
    if "mqtt_port" not in settings:
        raise RuntimeError("You need to specify an mqtt port")
    if "mqtt_user" not in settings:
        raise RuntimeError("No mqtt_user was specified")
    if "mqtt_password" not in settings:
        raise RuntimeError("No mqtt_password was specified")

    return settings


def binary_sensor_settings(path: str | None = None, cli: object = None) -> SettingsDict:
    """
    Load settings for a binary sensor
    """
    settings = load_mqtt_settings(path=path, cli=cli)
    cli_settings = cast(_BinarySensorCLISettings, cli)
    settings["state"] = cli_settings.state
    settings["metric_name"] = cli_settings.metric_name
    logger.debug(f"settings: {settings}")
    return settings


def device_settings(path: str | None = None, cli: object = None) -> SettingsDict:
    """
    Load settings for a device
    """
    settings = load_mqtt_settings(path=path, cli=cli)
    logger.debug(f"settings: {settings}")
    if "unique_id" not in settings:
        raise RuntimeError("No unique_id was specified")
    return settings
