"""Scene platform for Hatch devices.

One scene per favorite (Touch Ring preset or schedule). Hatch replaces a
favorite's record id whenever it is edited or reordered in the app, so each
scene follows a favorite slot (see ``favorite_slots``) rather than an id, and
scenes are added and removed as favorites come and go after each refresh.
"""

from __future__ import annotations

import logging
from typing import Any

from hatch_rest_api.iot_device import IotDevice
from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .commands import translate_command_errors
from .const import CONFIG_NUMBERED_PRESET_SCENES, CONFIG_NUMBERED_PRESET_SCENES_DEFAULT
from .favorite_slots import (
    favorite_id,
    favorite_name,
    favorite_scene_unique_id,
    favorite_scene_unique_id_prefix,
)
from .favorites import favorite_scene_attributes, favorite_scene_name
from .hatch_data_update_coordinator import HatchConfigEntry, HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HatchConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform from a config entry.

    Args:
        hass: Home Assistant instance.
        config_entry: The config entry.
        async_add_entities: The platform's add-entities callback.
    """
    coordinator = config_entry.runtime_data
    show_preset_numbers = bool(
        config_entry.options.get(
            CONFIG_NUMBERED_PRESET_SCENES,
            CONFIG_NUMBERED_PRESET_SCENES_DEFAULT,
        )
    )
    entities: dict[str, RiotScene] = {}

    async def async_reconcile() -> None:
        """Match the scenes to the favorite slots each device has now."""
        current: set[str] = set()
        prefixes: set[str] = set()
        new_entities: list[RiotScene] = []
        for rest_device in coordinator.rest_devices:
            if not isinstance(getattr(rest_device, "favorites", None), list):
                continue
            thing_name = rest_device.thing_name
            prefixes.add(favorite_scene_unique_id_prefix(thing_name))
            for slot_key in coordinator.favorites_by_slot(rest_device):
                unique_id = favorite_scene_unique_id(thing_name, slot_key)
                current.add(unique_id)
                if unique_id in entities:
                    continue
                entity = RiotScene(coordinator, thing_name, slot_key, show_preset_numbers)
                entities[unique_id] = entity
                new_entities.append(entity)

        for unique_id in [
            unique_id
            for unique_id in entities
            if unique_id not in current and unique_id.startswith(tuple(prefixes))
        ]:
            _LOGGER.debug("removing scene for deleted favorite: %s", unique_id)
            await entities.pop(unique_id).async_remove(force_remove=True)

        if prefixes:
            # Also drops scenes left behind by favorites that were edited or
            # deleted before favorites had slots, or while Home Assistant was
            # not running.
            registry = er.async_get(hass)
            for entry in er.async_entries_for_config_entry(registry, config_entry.entry_id):
                if (
                    entry.domain == "scene"
                    and entry.unique_id not in current
                    and entry.unique_id.startswith(tuple(prefixes))
                ):
                    _LOGGER.debug("removing stale scene registration: %s", entry.entity_id)
                    registry.async_remove(entry.entity_id)

        if new_entities:
            async_add_entities(new_entities)

    await async_reconcile()
    # Runs after every re-login, which is when favorites are fetched again.
    config_entry.async_on_unload(coordinator.async_add_alarm_refresh_callback(async_reconcile))


class RiotScene(HatchEntity[IotDevice], Scene):
    """Scene that starts the favorite in one favorite slot."""

    def __init__(
        self,
        coordinator: HatchDataUpdateCoordinator,
        thing_name: str,
        slot_key: str,
        show_preset_number: bool,
    ) -> None:
        """Initialize the scene.

        Args:
            coordinator: The integration's coordinator.
            thing_name: The device's AWS IoT thing name.
            slot_key: The favorite's slot.
            show_preset_number: Whether the name starts with the preset number.
        """
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type=f"Scene-{slot_key}",
        )
        self._attr_unique_id = favorite_scene_unique_id(thing_name, slot_key)
        # A scene is named after its favorite alone, as it always has been.
        self._attr_has_entity_name = False
        self._attr_translation_key = None
        self._slot_key = slot_key
        self._show_preset_number = show_preset_number
        _LOGGER.debug("scene; unique_id:%s, slot:%s", self._attr_unique_id, slot_key)

    def _favorite(self) -> tuple[int, dict[str, Any]] | None:
        """Return the slot's favorite now, with its preset number.

        Returns:
            The preset number and favorite, or None if the slot is empty.
        """
        rest_device = self.rest_device
        if rest_device is None:
            return None
        favorites = self.coordinator.favorites_by_slot(rest_device)
        for preset_number, (slot_key, favorite) in enumerate(favorites.items(), start=1):
            if slot_key == self._slot_key:
                return preset_number, favorite
        return None

    @property
    def available(self) -> bool:
        """Return whether the slot still holds a favorite."""
        return super().available and self._favorite() is not None

    @property
    def name(self) -> str | None:
        """Return the favorite's current name."""
        current = self._favorite()
        if current is None:
            return self.coordinator.favorite_slots.name(self.coordinator_context, self._slot_key)
        preset_number, favorite = current
        return favorite_scene_name(
            favorite_name(favorite) or "",
            preset_number,
            self._show_preset_number,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the favorite's current id and position."""
        current = self._favorite()
        if current is None:
            return None
        preset_number, favorite = current
        return favorite_scene_attributes(favorite, preset_number)

    @translate_command_errors
    async def async_activate(self, **kwargs: Any) -> None:
        """Start the slot's favorite under its current Hatch id.

        Args:
            **kwargs: Unused scene activation arguments.

        Raises:
            HomeAssistantError: The favorite no longer exists.
        """
        current = self._favorite()
        rest_device = self.rest_device
        if current is None or rest_device is None:
            raise HomeAssistantError(f"Hatch favorite for {self.entity_id} no longer exists")
        _, favorite = current
        favorite_name_id = f"{favorite_name(favorite)}-{favorite_id(favorite)}"
        _LOGGER.debug("activating scene:%s with %s", self.unique_id, favorite_name_id)
        await rest_device.async_command(rest_device.set_favorite, favorite_name_id)
