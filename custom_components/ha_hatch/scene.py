from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import (
    CONFIG_NUMBERED_PRESET_SCENES,
    CONFIG_NUMBERED_PRESET_SCENES_DEFAULT,
    DOMAIN,
)
from .favorites import favorite_scene_attributes, favorite_scene_name
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    show_preset_numbers = bool(
        config_entry.options.get(
            CONFIG_NUMBERED_PRESET_SCENES,
            CONFIG_NUMBERED_PRESET_SCENES_DEFAULT,
        )
    )
    scene_entities: list[RiotScene] = []
    for rest_device in coordinator.rest_devices:
        if hasattr(rest_device, "favorites") and isinstance(rest_device.favorites, list):
            for preset_number, favorite in enumerate(rest_device.favorites, start=1):
                try:
                    favorite_name = favorite["steps"][0]["name"]
                    favorite_id = favorite["id"]
                except (TypeError, KeyError, IndexError):
                    _LOGGER.error(
                        f"Error creating scene for {rest_device.thing_name} "
                        f"with favorite {favorite}. Skipping this favorite."
                    )
                    continue
                scene_entities.append(
                    RiotScene(
                        coordinator,
                        rest_device.thing_name,
                        favorite_scene_name(
                            favorite_name,
                            preset_number,
                            show_preset_numbers,
                        ),
                        favorite_name,
                        favorite_id,
                        favorite_scene_attributes(favorite, preset_number),
                    )
                )
    async_add_entities(scene_entities)


class RiotScene(HatchEntity, Scene):
    def __init__(
        self,
        coordinator: HatchDataUpdateCoordinator,
        thing_name: str,
        name: str,
        favorite_name: str,
        favorite_id: int,
        extra_state_attributes: dict[str, Any],
    ) -> None:
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type=f"Scene-{favorite_name}-{favorite_id}",
        )
        self._attr_name = name
        self._attr_extra_state_attributes = extra_state_attributes
        self.favorite_name_id = f"{favorite_name}-{favorite_id}"
        _LOGGER.debug(
            f"scene; unique_id:{self._attr_unique_id}, "
            f"name:{self._attr_name}, favorite_name_id:{self.favorite_name_id}"
        )

    def activate(self, **kwargs: Any) -> None:
        _LOGGER.debug(f"activating scene:{self.unique_id}")
        self.rest_device.set_favorite(self.favorite_name_id)
