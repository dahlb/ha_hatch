# brightness
from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from hatch_rest_api import RestMini

from .const import DOMAIN, DATA_REST_DEVICES, DATA_SENSORS
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    hass.data.setdefault(DOMAIN, {})

    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    sensor_entities = []
    for rest_device in rest_devices:
        if not isinstance(rest_device, RestMini):
            sensor_entities.append(HatchBattery(rest_device))
    hass.data[DOMAIN][DATA_SENSORS] = sensor_entities
    async_add_entities(sensor_entities)


class HatchBattery(RestEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_icon = "mdi:battery"

    def __init__(self, rest_device: RestPlus):
        super().__init__(rest_device, "Battery")

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        self._attr_native_value = self.rest_device.battery_level
        self.async_write_ha_state()
