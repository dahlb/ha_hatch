from __future__ import annotations

from logging import getLogger
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity, BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import DOMAIN
from .hatch_entity import HatchEntity

_LOGGER = getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]

    binary_sensor_entities = [HatchOnlineSensor(coordinator=coordinator, thing_name=rest_device.thing_name) for rest_device in coordinator.rest_devices]
    async_add_entities(binary_sensor_entities)


class HatchOnlineSensor(HatchEntity, BinarySensorEntity):
    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Wifi")
        self.entity_description = BinarySensorEntityDescription(
            key=f"#{self._attr_unique_id}-online",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            icon="mdi:wifi-check",
        )

    def is_on(self) -> bool:
        return self.rest_device.is_online

    @property
    def icon(self) -> str | None:
        if self.is_on:
            return self.entity_description.icon
        else:
            return "mdi:wifi-strength-outline"
