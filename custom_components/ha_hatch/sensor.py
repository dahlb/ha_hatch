# brightness
from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from hatch_rest_api import RestPlus, RestIot
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_REST_DEVICES, DATA_SENSORS
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hass.data.setdefault(DOMAIN, {})

    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    sensor_entities = []
    for rest_device in rest_devices:
        if isinstance(rest_device, RestPlus) or isinstance(rest_device, RestIot):
            sensor_entities.append(HatchBattery(rest_device))
        if isinstance(rest_device, RestIot):
            sensor_entities.append(HatchCharging(rest_device))
    hass.data[DOMAIN][DATA_SENSORS] = sensor_entities
    async_add_entities(sensor_entities)


class HatchBattery(RestEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        icon="mdi:battery",
        native_unit_of_measurement=PERCENTAGE,
    )

    def __init__(self, rest_device: RestPlus | RestIot):
        super().__init__(rest_device, "Battery")

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        self._attr_native_value = self.rest_device.battery_level
        self.schedule_update_ha_state()


class HatchCharging(RestEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="charging",
        icon="mdi:power-plug",
    )

    def __init__(self, rest_device: RestIot):
        super().__init__(rest_device, "Charging Status")

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        if self.rest_device.charging_status == 0:
            self._attr_native_value = "Not Charging"
        if self.rest_device.charging_status == 3:
            self._attr_native_value = "Charging, plugged in"
        if self.rest_device.charging_status == 5:
            self._attr_native_value = "Charging, on base"
        self.schedule_update_ha_state()

    @property
    def icon(self) -> str | None:
        if self._attr_native_value == "Not Charging":
            return "mdi:power-plug-off"
        else:
            return self.entity_description.icon
