"""Binary sensor platform for Hatch devices."""

from __future__ import annotations

from logging import getLogger

from hatch_rest_api import RestDevice
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hatch_data_update_coordinator import HatchConfigEntry, HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity

_LOGGER = getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: HatchConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the platform from a config entry."""
    coordinator = config_entry.runtime_data

    binary_sensor_entities = [
        HatchOnlineSensor(coordinator=coordinator, thing_name=rest_device.thing_name)
        for rest_device in coordinator.rest_devices
    ]
    async_add_entities(binary_sensor_entities)


class HatchOnlineSensor(HatchEntity[RestDevice], BinarySensorEntity):
    """Hatch online sensor."""

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the hatch online sensor."""
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Wifi")
        self.entity_description = BinarySensorEntityDescription(
            key=f"#{self._attr_unique_id}-online",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            icon="mdi:wifi-check",
        )

    @property
    def is_on(self) -> bool:
        """Return whether the entity is on."""
        return bool(self.rest_device.is_online)

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self.is_on:
            return self.entity_description.icon
        return "mdi:wifi-strength-outline"
