from __future__ import annotations

import logging
from hatch_rest_api import RestPlus, RestMini, RestIot, RestoreIot
from homeassistant.helpers.entity import DeviceInfo
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HatchDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class HatchEntity(CoordinatorEntity[HatchDataUpdateCoordinator]):
    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str, entity_type: str):
        super().__init__(coordinator=coordinator, context=thing_name)
        self._attr_unique_id = (
            f"{thing_name}_{entity_type.lower().replace(' ', '_')}"
        )
        self._attr_name = f"{self.rest_device.device_name} {entity_type}"
        connections = {
            (
                dr.CONNECTION_NETWORK_MAC,
                self.rest_device.mac.lower(),
            ),  # api reported mac address
            (
                dr.CONNECTION_NETWORK_MAC,
                f"{self.rest_device.mac[:-1].lower()}0",
            ),  # device network detected mac address
        }
        self._attr_device_info = DeviceInfo(
            connections=connections,
            identifiers={(DOMAIN, thing_name)},
            manufacturer="Hatch",
            model=self.rest_device.__class__.__name__,
            name=self.rest_device.device_name,
            sw_version=self.rest_device.firmware_version,
        )

    @property
    def rest_device(self) -> RestPlus | RestMini | RestIot | RestoreIot:
        return self.coordinator.rest_device_by_thing_name(self.coordinator_context)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.schedule_update_ha_state()
