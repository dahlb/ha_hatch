from __future__ import annotations

import logging
from hatch_rest_api import RestPlus, RestIot, RestoreIot
from .rest_light_entity import RestLightEntity
from .riot_light_entity import RiotLightEntity
from .restoreiot_light_entity import RestoreIotLightEntity
from .riot_clock_entity import RiotClockEntity

from .const import (
    DOMAIN,
    DATA_REST_DEVICES,
    DATA_LIGHTS,
    CONFIG_TURN_ON_LIGHT,
    CONFIG_TURN_ON_DEFAULT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    hass.data.setdefault(DOMAIN, {})
    config_turn_on_light = config_entry.options.get(
        CONFIG_TURN_ON_LIGHT, CONFIG_TURN_ON_DEFAULT
    )

    _LOGGER.debug(
        f"setting up hatch lights, auto turn on switch set to {config_turn_on_light}"
    )
    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    light_entities = []
    for rest_device in rest_devices:
        if isinstance(rest_device, RestPlus):
            light_entities.append(RestLightEntity(rest_device, config_turn_on_light))
        elif isinstance(rest_device, RestIot):
            light_entities.append(RiotLightEntity(rest_device))
            light_entities.append(RiotClockEntity(rest_device))
        elif isinstance(rest_device, RestoreIot):
            light_entities.append(RestoreIotLightEntity(rest_device))
            light_entities.append(RiotClockEntity(rest_device))

    hass.data[DOMAIN][DATA_LIGHTS] = light_entities
    async_add_entities(light_entities)
