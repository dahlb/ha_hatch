from __future__ import annotations

import logging
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass,
)
from hatch_rest_api import RestPlus

from .const import DOMAIN, DATA_REST_DEVICES, DATA_SWITCHES
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    hass.data.setdefault(DOMAIN, {})

    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    entities = []
    for rest_device in rest_devices:
        if isinstance(rest_device, RestPlus):
            entities.append(HatchPowerSwitch(rest_device))
    hass.data[DOMAIN][DATA_SWITCHES] = entities
    async_add_entities(entities)


class HatchPowerSwitch(RestEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, rest_device: RestPlus):
        super().__init__(rest_device, "Power Switch")

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        self._attr_is_on = self.rest_device.is_on
        self.async_write_ha_state()

    def turn_on(self, **kwargs):
        self.rest_device.set_on(True)

    def turn_off(self, **kwargs):
        self.rest_device.set_on(False)
