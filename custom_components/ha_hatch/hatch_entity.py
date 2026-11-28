"""Base entity for Hatch devices."""

from __future__ import annotations

import logging
from typing import cast

from hatch_rest_api.shadow_client_subscriber import ShadowClientSubscriberMixin
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hatch_data_update_coordinator import HatchDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HatchEntity[DeviceT: ShadowClientSubscriberMixin](
    CoordinatorEntity[HatchDataUpdateCoordinator]
):
    """Base class for Hatch entities.

    ``DeviceT`` is the hatch_rest_api class, or shared base class, of the devices
    the entity is created for, such as ``HatchEntity[RestPlus]``.
    """

    def __init__(
        self, coordinator: HatchDataUpdateCoordinator, thing_name: str, entity_type: str
    ) -> None:
        """Initialize the hatch entity."""
        super().__init__(coordinator=coordinator, context=thing_name)
        self._attr_unique_id = f"{thing_name}_{entity_type.lower().replace(' ', '_')}"
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
            sw_version=getattr(self.rest_device, "firmware_version", None),
        )

    @property
    def available(self) -> bool:
        """Whether the coordinator is up and still has this entity's device.

        A reconnect replaces every device, and one removed from the account in
        the meantime is gone; its entities are then unavailable.
        """
        return (
            super().available
            and self.coordinator.rest_device_by_thing_name(self.coordinator_context) is not None
        )

    @property
    def rest_device(self) -> DeviceT:
        """Return the Hatch device for this entity.

        Home Assistant only reads an entity's state while it is ``available``,
        which requires the device, so the device is typed as always present.
        """
        return cast("DeviceT", self.coordinator.rest_device_by_thing_name(self.coordinator_context))

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.schedule_update_ha_state()
