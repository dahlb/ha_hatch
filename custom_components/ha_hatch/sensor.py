# brightness
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from hatch_rest_api import RestPlus, RestIot
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import HatchDataUpdateCoordinator
from .const import DOMAIN
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hass.data.setdefault(DOMAIN, {})

    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    sensor_entities = []
    for rest_device in coordinator.rest_devices:
        if isinstance(rest_device, RestPlus) or isinstance(rest_device, RestIot):
            sensor_entities.append(HatchBattery(coordinator=coordinator, thing_name=rest_device.thing_name))
        if isinstance(rest_device, RestIot):
            sensor_entities.append(HatchCharging(coordinator=coordinator, thing_name=rest_device.thing_name))
    async_add_entities(sensor_entities)


class HatchBattery(HatchEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        icon="mdi:battery",
        native_unit_of_measurement=PERCENTAGE,
    )

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Battery")

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        return self.rest_device.battery_level


class HatchCharging(HatchEntity, SensorEntity):
    entity_description = SensorEntityDescription(
        key="charging",
        icon="mdi:power-plug",
    )

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Charging Status")

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        if self.rest_device.charging_status == 0:
            return "Not Charging"
        if self.rest_device.charging_status == 3:
            return "Charging, plugged in"
        if self.rest_device.charging_status == 5:
            return "Charging, on base"

    @property
    def icon(self) -> str | None:
        if self._attr_native_value == "Not Charging":
            return "mdi:power-plug-off"
        else:
            return self.entity_description.icon
