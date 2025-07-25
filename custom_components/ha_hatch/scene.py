from __future__ import annotations

import logging
from homeassistant.components.scene import Scene
from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import DOMAIN
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    scene_entities = []
    for rest_device in coordinator.rest_devices:
        if hasattr(rest_device, "favorites") and isinstance(rest_device.favorites, list):
            for favorite in rest_device.favorites:
                try:
                    favorite_name, favorite_id = favorite['steps'][0]['name'], favorite['id']
                except (TypeError, KeyError, IndexError):
                    _LOGGER.error(f"Error creating scene for {rest_device.thing_name} with favorite {favorite}. Skipping this favorite.")
                    continue
                scene_entities.append(RiotScene(coordinator, rest_device.thing_name, favorite_name, favorite_id))
    async_add_entities(scene_entities)


class RiotScene(HatchEntity, Scene):
    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str, name: str, favorite_id: int):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type=f"Scene-{name}")
        self._attr_name = name
        self.favorite_name_id = f"{name}-{favorite_id}"
        _LOGGER.debug(f"scene; unique_id:{self._attr_unique_id}, name:{self._attr_name}, favorite_name_id:{self.favorite_name_id}")

    def activate(self, **kwargs: Any) -> None:
        _LOGGER.debug(f"activating scene:{self.unique_id}")
        self.rest_device.set_favorite(self.favorite_name_id)
