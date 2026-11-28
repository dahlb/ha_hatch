"""The Hatch integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .hatch_data_update_coordinator import (
    FAVORITE_SLOTS_STORE_VERSION,
    RESTORE_ALARM_SLOTS_STORE_VERSION,
    HatchDataUpdateCoordinator,
    favorite_slots_store_key,
    restore_alarm_slots_store_key,
)
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the Hatch integration."""
    async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up the platform from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    email = config_entry.data[CONF_EMAIL]
    password = config_entry.data[CONF_PASSWORD]

    hass.data[DOMAIN] = HatchDataUpdateCoordinator(
        hass=hass,
        email=email,
        password=password,
        config_entry=config_entry,
    )

    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    await coordinator.async_load_restore_alarm_slots()
    await coordinator.async_load_favorite_slots()
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    coordinator.async_start_alarm_refresh()

    if not config_entry.update_listeners:
        config_entry.add_update_listener(async_update_options)

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("unload entry")
    coordinator: HatchDataUpdateCoordinator | None = hass.data.get(DOMAIN)
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        if coordinator is not None:
            await coordinator.async_shutdown()
        hass.data[DOMAIN] = None

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Drop the alarm and favorite slots stored for a removed entry.

    Args:
        hass: Home Assistant instance.
        config_entry: The entry being removed.
    """
    await Store(
        hass,
        RESTORE_ALARM_SLOTS_STORE_VERSION,
        restore_alarm_slots_store_key(config_entry.entry_id),
    ).async_remove()
    await Store(
        hass,
        FAVORITE_SLOTS_STORE_VERSION,
        favorite_slots_store_key(config_entry.entry_id),
    ).async_remove()
