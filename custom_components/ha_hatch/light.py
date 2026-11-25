"""Light platform for Hatch devices."""

from __future__ import annotations

from logging import getLogger

from hatch_rest_api import RestBaby, RestIot, Restore, RestoreIot, RestoreV5, RestPlus
from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import CONFIG_TURN_ON_DEFAULT, CONFIG_TURN_ON_LIGHT, DOMAIN
from .light_rest_entity import LightRestEntity
from .light_restoreiot_entity import LightRestoreIotEntity
from .light_riot_clock_entity import LightRiotClockEntity
from .light_riot_entity import LightRiotEntity
from .restore_entities import RestoreClockLight, RestoreLight

_LOGGER = getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the platform from a config entry."""
    config_turn_on_light = config_entry.options.get(CONFIG_TURN_ON_LIGHT, CONFIG_TURN_ON_DEFAULT)
    _LOGGER.debug("setting up hatch lights, auto turn on switch set to %s", config_turn_on_light)
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    light_entities: list[LightEntity] = []
    for rest_device in coordinator.rest_devices:
        if isinstance(rest_device, RestPlus):
            light_entities.append(
                LightRestEntity(
                    coordinator=coordinator,
                    thing_name=rest_device.thing_name,
                    config_turn_on_light=config_turn_on_light,
                )
            )
        elif isinstance(rest_device, RestoreIot | RestoreV5):
            light_entities.append(
                LightRestoreIotEntity(coordinator=coordinator, thing_name=rest_device.thing_name)
            )
            light_entities.append(
                LightRiotClockEntity(coordinator=coordinator, thing_name=rest_device.thing_name)
            )
        elif isinstance(rest_device, Restore):
            light_entities.append(
                RestoreLight(coordinator=coordinator, thing_name=rest_device.thing_name)
            )
            light_entities.append(
                RestoreClockLight(coordinator=coordinator, thing_name=rest_device.thing_name)
            )
        elif isinstance(rest_device, RestIot | RestBaby):
            light_entities.append(
                LightRiotEntity(coordinator=coordinator, thing_name=rest_device.thing_name)
            )
            light_entities.append(
                LightRiotClockEntity(coordinator=coordinator, thing_name=rest_device.thing_name)
            )

    async_add_entities(light_entities)
