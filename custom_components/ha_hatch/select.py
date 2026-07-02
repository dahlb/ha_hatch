from __future__ import annotations

import logging

from hatch_rest_api import RestoreV5
from hatch_rest_api.const import RIOT_FLAGS_CLOCK_ON
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import DOMAIN
from .hatch_entity import HatchEntity

_LOGGER = logging.getLogger(__name__)

MODE_ALWAYS_ON = "Always On"
MODE_ALWAYS_OFF = "Always Off"
MODE_OFF_AT_NIGHT = "Off at Night"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    entities = []
    for rest_device in coordinator.rest_devices:
        # RestoreV4 subclasses RestoreV5, so this covers both.
        if isinstance(rest_device, RestoreV5):
            entities.append(
                ClockModeSelect(
                    coordinator=coordinator,
                    thing_name=rest_device.thing_name,
                )
            )
    async_add_entities(entities)


class ClockModeSelect(HatchEntity, SelectEntity):
    _attr_icon = "mdi:clock-time-four-outline"
    _attr_options = [MODE_ALWAYS_ON, MODE_OFF_AT_NIGHT, MODE_ALWAYS_OFF]

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Clock Mode",
        )

    @property
    def current_option(self) -> str | None:
        dev = self.rest_device
        mode = getattr(dev, "clock_turn_off_mode", None)
        if mode == "always":
            return MODE_ALWAYS_OFF
        if mode == "custom":
            return MODE_OFF_AT_NIGHT
        if mode == "never":
            return MODE_ALWAYS_ON
        # Fall back to the display flag until the mode field has been parsed.
        return MODE_ALWAYS_OFF if not dev.is_clock_on else MODE_ALWAYS_ON

    def select_option(self, option: str) -> None:
        dev = self.rest_device
        if option == MODE_ALWAYS_OFF:
            dev._update(
                {
                    "clock": {
                        "flags": dev.flags & ~RIOT_FLAGS_CLOCK_ON,
                        "turnOffMode": "always",
                    }
                }
            )
        elif option == MODE_ALWAYS_ON:
            dev._update(
                {
                    "clock": {
                        "flags": dev.flags | RIOT_FLAGS_CLOCK_ON,
                        "turnOffMode": "never",
                    }
                }
            )
        elif option == MODE_OFF_AT_NIGHT:
            dev._update(
                {
                    "clock": {
                        "flags": dev.flags | RIOT_FLAGS_CLOCK_ON,
                        "turnOffMode": "custom",
                    }
                }
            )
