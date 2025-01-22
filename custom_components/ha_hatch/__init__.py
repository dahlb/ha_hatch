import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, HassJob
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    Platform,
)
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
import datetime

from .const import (
    DOMAIN,
    DATA_MQTT_CONNECTION,
    DATA_REST_DEVICES,
    DATA_EXPIRATION_LISTENER,
    DATA_ENTITIES_KEYS,
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

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.LIGHT, Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH, Platform.SCENE]


async def async_setup(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("async setup")
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    email = config_entry.data[CONF_EMAIL]
    password = config_entry.data[CONF_PASSWORD]

    data = {}

    async def setup_connection(time: datetime) -> None:
        _LOGGER.debug(f"updating credentials: {time}")
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
            client_session=client_session,
            on_connection_interrupted=disconnect,
            on_connection_resumed=resumed,
        )
        _LOGGER.debug(
            f"credentials expire at: {datetime.datetime.fromtimestamp(expiration_time, datetime.UTC)}"
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
            HassJob(target=setup_connection, name="Hatch Update Credentials", cancel_on_shutdown=True),
            datetime.datetime.fromtimestamp(expiration_time - 60, datetime.UTC),
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
