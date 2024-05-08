from __future__ import annotations

import logging
from homeassistant.components.scene import Scene
from typing import Any
from hatch_rest_api import RestIot

from .const import DOMAIN, DATA_REST_DEVICES, DATA_SENSORS
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    hass.data.setdefault(DOMAIN, {})

    rest_devices = hass.data[DOMAIN][DATA_REST_DEVICES]
    scene_entities = []
    for rest_device in rest_devices:
        if isinstance(rest_device, RestIot):
            for favorite in rest_device.favorites:
                if len(favorite['steps']) > 0:
                    scene_entities.append(RiotScene(rest_device, favorite['steps'][0]['name'], favorite['id']))
    hass.data[DOMAIN][DATA_SENSORS] = scene_entities
    async_add_entities(scene_entities)


class RiotScene(RestEntity, Scene):
    def __init__(self, rest_device: RestIot, name: str, favorite_id: int):
        super().__init__(rest_device, f"Scene-{name}-{favorite_id}")
        self._attr_name = name
        self.favorite_name_id = f"{name}-{favorite_id}"

    def activate(self, **kwargs: Any) -> None:
        self.rest_device.set_favorite(self.favorite_name_id)

    def _update_local_state(self):
        pass
