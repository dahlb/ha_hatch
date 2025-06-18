from __future__ import annotations

from logging import getLogger
from hatch_rest_api import RestPlus, RestIot, RestoreIot, RestoreV5
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .light_rest_entity import LightRestEntity
from .light_riot_entity import LightRiotEntity
from .light_restoreiot_entity import LightRestoreIotEntity
from .light_riot_clock_entity import LightRiotClockEntity

from .const import (
    DOMAIN,
    CONFIG_TURN_ON_LIGHT,
    CONFIG_TURN_ON_DEFAULT,
)

_LOGGER = getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    config_turn_on_light = config_entry.options.get(
        CONFIG_TURN_ON_LIGHT, CONFIG_TURN_ON_DEFAULT
    )
    _LOGGER.debug(f"setting up hatch lights, auto turn on switch set to {config_turn_on_light}")
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    light_entities = []
    for rest_device in coordinator.rest_devices:
        if isinstance(rest_device, RestPlus):
            light_entities.append(LightRestEntity(coordinator=coordinator, thing_name=rest_device.thing_name, config_turn_on_light=config_turn_on_light))
        elif isinstance(rest_device, RestoreIot | RestoreV5):
            light_entities.append(LightRestoreIotEntity(coordinator=coordinator, thing_name=rest_device.thing_name))
            light_entities.append(LightRiotClockEntity(coordinator=coordinator, thing_name=rest_device.thing_name))
        elif isinstance(rest_device, RestIot):
            light_entities.append(LightRiotEntity(coordinator=coordinator, thing_name=rest_device.thing_name))
            light_entities.append(LightRiotClockEntity(coordinator=coordinator, thing_name=rest_device.thing_name))

    async_add_entities(light_entities)
