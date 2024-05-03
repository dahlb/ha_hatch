from __future__ import annotations

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityDescription
from hatch_rest_api import RestPlus, RestMini, RestIot

from .const import DOMAIN, DATA_REST_DEVICES, DATA_BINARY_SENSORS
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    hass.data.setdefault(DOMAIN, {})

    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    binary_sensor_entities = [HatchOnlineSensor(rest_device) for rest_device in rest_devices]
    hass.data[DOMAIN][DATA_BINARY_SENSORS] = binary_sensor_entities
    async_add_entities(binary_sensor_entities)


class HatchOnlineSensor(RestEntity, BinarySensorEntity):
    _attr_icon = "mdi:wifi-check"

    def __init__(self, rest_device: RestIot | RestMini | RestPlus):
        super().__init__(rest_device, "Wifi")
        self.entity_description = EntityDescription(
            key=f"#{self._attr_unique_id}-online",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
        )

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        self._attr_is_on = self.rest_device.is_online
        self.schedule_update_ha_state()

    @property
    def icon(self) -> str | None:
        if self.is_on:
            return self._attr_icon
        else:
            return "mdi:wifi-strength-outline"
