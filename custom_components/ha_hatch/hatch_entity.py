"""Base entity for Hatch devices."""

from __future__ import annotations

from collections.abc import Mapping
import logging
import re
from typing import cast

from hatch_rest_api.shadow_client_subscriber import ShadowClientSubscriberMixin
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hatch_data_update_coordinator import HatchDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def entity_translation_key(entity_type: str) -> str:
    """Return the translation key for an entity type, e.g. ``clock_24_hour``.

    Args:
        entity_type: The entity type, such as "Clock 24-Hour".

    Returns:
        The entity type in lower case, with each run of other characters as ``_``.
    """
    return re.sub(r"[^a-z0-9]+", "_", entity_type.lower()).strip("_")


class HatchEntity[DeviceT: ShadowClientSubscriberMixin](
    CoordinatorEntity[HatchDataUpdateCoordinator]
):
    """Base class for Hatch entities.

    ``DeviceT`` is the hatch_rest_api class, or shared base class, of the devices
    the entity is created for, such as ``HatchEntity[RestPlus]``.

    The entity is named by its ``translation_key`` (from ``strings.json``), and
    Home Assistant puts the device's name in front of it, so renaming a device
    renames its entities.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HatchDataUpdateCoordinator,
        thing_name: str,
        entity_type: str,
        *,
        translation_key: str | None = None,
        translation_placeholders: Mapping[str, str] | None = None,
    ) -> None:
        """Initialize the hatch entity.

        Args:
            coordinator: The account's coordinator.
            thing_name: The device's AWS IoT thing name.
            entity_type: What the entity is, such as "Light"; it makes the unique id
                and, unless ``translation_key`` is given, the translation key.
            translation_key: The entity's translation key, if not from ``entity_type``.
            translation_placeholders: Values for the placeholders in the name.
        """
        super().__init__(coordinator=coordinator, context=thing_name)
        self._attr_unique_id = f"{thing_name}_{entity_type.lower().replace(' ', '_')}"
        self._attr_translation_key = translation_key or entity_translation_key(entity_type)
        if translation_placeholders is not None:
            self._attr_translation_placeholders = dict(translation_placeholders)
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
