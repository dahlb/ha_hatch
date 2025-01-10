from __future__ import annotations

import logging
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass, SwitchEntityDescription,
)
from hatch_rest_api import RestPlus, RestIot
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_REST_DEVICES, DATA_SWITCHES
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hass.data.setdefault(DOMAIN, {})

    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    entities = []
    for rest_device in rest_devices:
        if isinstance(rest_device, RestPlus):
            entities.append(HatchPowerSwitch(rest_device))
        if isinstance(rest_device, RestIot):
            entities.append(HatchToddlerLockSwitch(rest_device))
    hass.data[DOMAIN][DATA_SWITCHES] = entities
    async_add_entities(entities)


class HatchPowerSwitch(RestEntity, SwitchEntity):
    entity_description: SwitchEntityDescription(
        key="power-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )

    def __init__(self, rest_device: RestPlus):
        super().__init__(rest_device, "Power Switch")

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        self._attr_is_on = self.rest_device.is_on
        self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        self.rest_device.set_on(True)

    def turn_off(self, **kwargs):
        self.rest_device.set_on(False)


class HatchToddlerLockSwitch(RestEntity, SwitchEntity):
    entity_description: SwitchEntityDescription(
        key="toddler-lock",
        icon="mdi:human-child",
        device_class=SwitchDeviceClass.SWITCH,
    )

    def __init__(self, rest_device: RestIot):
        super().__init__(rest_device, "Toddler Lock")

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        self._attr_is_on = self.rest_device.toddler_lock
        self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        self.rest_device.set_toddler_lock(True)

    def turn_off(self, **kwargs):
        self.rest_device.set_toddler_lock(False)
