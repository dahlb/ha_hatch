# brightness
from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import PERCENTAGE
from hatch_rest_api import RestMini, RestPlus

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
            sensor_entities.append(HatchCharging(rest_device))
    hass.data[DOMAIN][DATA_SENSORS] = sensor_entities
    async_add_entities(sensor_entities)


class HatchBattery(RestEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:battery"

    def __init__(self, rest_device: RestPlus):
        super().__init__(rest_device, "Battery")

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        self._attr_native_value = self.rest_device.battery_level
        self.async_write_ha_state()


class HatchCharging(RestEntity, SensorEntity):
    _attr_icon = "mdi:power-plug"

    def __init__(self, rest_device: RestPlus):
        super().__init__(rest_device, "Charging Status")

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        if self.rest_device.charging_status is 0:
            self._attr_native_value = "Not Charging"
        if self.rest_device.charging_status is 3:
            self._attr_native_value = "Charging, plugged in"
        if self.rest_device.charging_status is 5:
            self._attr_native_value = "Charging, on base"
        self.async_write_ha_state()

    @property
    def icon(self) -> str | None:
        if self._attr_native_value is "Not Charging":
            return "mdi:power-plug-off"
        else:
            return self._attr_icon
