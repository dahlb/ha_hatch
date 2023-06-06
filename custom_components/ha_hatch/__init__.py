import logging

import distro
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.requirements import RequirementsNotFound
from homeassistant.util.package import (
    install_package,
    is_installed,
    is_virtual_env,
    is_docker_env,
)
import datetime
from subprocess import PIPE, Popen
import os

from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_MQTT_CONNECTION,
    DATA_REST_DEVICES,
    DATA_EXPIRATION_LISTENER,
    DATA_ENTITIES_KEYS,
    API_VERSION,
)
from .util import find_rest_device_by_thing_name

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _install_distro_packages(args, errMsg="Unable to install package dependencies"):
    if os.geteuid() != 0:
        args.insert(0, "sudo")
    with Popen(
        args, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=os.environ.copy()
    ) as process:
        _, stderr = process.communicate()
        if process.returncode != 0:
            _LOGGER.error(errMsg)
            try:
                _LOGGER.error(stderr.decode("utf-8").lstrip().strip())
            except Exception as error:
                _LOGGER.error(error)


def _install_package_dependencies():
    if is_docker_env() and not is_virtual_env():
        distro_id = distro.id()
        if distro_id == "alpine":
            _install_distro_packages(["apk", "add", "gcc", "g++", "cmake", "make"])
        elif distro_id == "debian" or distro_id == "ubuntu":
            _install_distro_packages(
                ["apt-get", "update"], "Failed to update available packages"
            )
            _install_distro_packages(
                ["apt-get", "install", "build-essential", "cmake", "-y"]
            )
        else:
            _LOGGER.warning(
                """Unsupported distro: %s. If you run into issues, make sure you have
                gcc, g++, cmake, and make installed in your Home Assistant container.""",
                distro_id,
            )


def _lazy_install():
    _install_package_dependencies()
    custom_required_packages = [f"hatch-rest-api=={API_VERSION}"]
    links = "https://qqaatw.github.io/aws-crt-python-musllinux/"
    for pkg in custom_required_packages:
        if not is_installed(pkg) and not install_package(pkg, find_links=links):
            raise RequirementsNotFound(DOMAIN, [pkg])


async def async_setup(hass: HomeAssistant, config_entry: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("async setup")
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _lazy_install()
    email = config_entry.data[CONF_EMAIL]
    password = config_entry.data[CONF_PASSWORD]

    data = {}

    async def setup_connection(arg):
        _LOGGER.debug(f"updating credentials: {arg}")
        client_session = async_get_clientsession(hass)

        def disconnect():
            _LOGGER.debug("disconnected")

        def resumed():
            _LOGGER.debug("resumed")

        from awscrt.mqtt import Connection

        if DATA_MQTT_CONNECTION in data:
            mqtt_connection: Connection = data[DATA_MQTT_CONNECTION]
            try:
                mqtt_connection.disconnect().result()
            except Exception as error:
                _LOGGER.debug(
                    f"mqtt_connection disconnect failed during reconnect: {error}"
                )

        from hatch_rest_api import get_rest_devices

        _, mqtt_connection, rest_devices, expiration_time = await get_rest_devices(
            email=email,
            password=password,
            client_session=None,
            on_connection_interrupted=disconnect,
            on_connection_resumed=resumed,
        )
        _LOGGER.debug(
            f"credentials expire at: {datetime.datetime.fromtimestamp(expiration_time)}"
        )
        data[DATA_MQTT_CONNECTION] = mqtt_connection
        data[DATA_REST_DEVICES] = rest_devices

        for entity_key in DATA_ENTITIES_KEYS:
            if entity_key in data:
                for entity in data[entity_key]:
                    entity.replace_rest_device(
                        find_rest_device_by_thing_name(
                            rest_devices, entity.rest_device.thing_name
                        )
                    )

        data[DATA_EXPIRATION_LISTENER] = async_track_point_in_utc_time(
            hass,
            setup_connection,
            datetime.datetime.fromtimestamp(expiration_time - 60),
        )

    await setup_connection("initial setup")

    hass.data[DOMAIN] = data

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    if not config_entry.update_listeners:
        config_entry.add_update_listener(async_update_options)

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug("unload entry")
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        mqtt_connection = hass.data[DOMAIN][DATA_MQTT_CONNECTION]
        try:
            mqtt_connection.disconnect().result()
        except Exception as error:
            _LOGGER.debug(f"mqtt_connection disconnect failed during unload: {error}")
        config_auth_expiration_listener = hass.data[DOMAIN][DATA_EXPIRATION_LISTENER]
        config_auth_expiration_listener()

        hass.data[DOMAIN] = None

    return unload_ok
