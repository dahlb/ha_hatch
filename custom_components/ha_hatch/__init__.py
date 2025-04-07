import logging

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
)
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    PLATFORMS,
)
from .hatch_data_update_coordinator import HatchDataUpdateCoordinator
from .util import find_rest_device_by_thing_name

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    email = config_entry.data[CONF_EMAIL]
    password = config_entry.data[CONF_PASSWORD]


    hass.data[DOMAIN] = HatchDataUpdateCoordinator(
        hass=hass,
        email=email,
        password=password
    )

    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    await coordinator.async_config_entry_first_refresh()

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
        hass.data[DOMAIN] = None

    return unload_ok
