"""Select platform for Hatch devices."""

from __future__ import annotations

import logging
from typing import ClassVar

from hatch_rest_api import Restore, RestoreV5
from hatch_rest_api.const import (
    CLOCK_TURN_OFF_MODE_ALWAYS,
    CLOCK_TURN_OFF_MODE_CUSTOM,
    CLOCK_TURN_OFF_MODE_NEVER,
)
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HatchDataUpdateCoordinator
from .const import DOMAIN
from .hatch_entity import HatchEntity
from .restore_entities import RestoreClockMode, RestoreRoutineStep

_LOGGER = logging.getLogger(__name__)

MODE_ALWAYS_ON = "Always On"
MODE_ALWAYS_OFF = "Always Off"
MODE_OFF_AT_NIGHT = "Off at Night"

OPTION_TO_TURN_OFF_MODE = {
    MODE_ALWAYS_ON: CLOCK_TURN_OFF_MODE_NEVER,
    MODE_OFF_AT_NIGHT: CLOCK_TURN_OFF_MODE_CUSTOM,
    MODE_ALWAYS_OFF: CLOCK_TURN_OFF_MODE_ALWAYS,
}
TURN_OFF_MODE_TO_OPTION = {mode: option for option, mode in OPTION_TO_TURN_OFF_MODE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform from a config entry."""
    coordinator: HatchDataUpdateCoordinator = hass.data[DOMAIN]
    # RestoreV4 subclasses RestoreV5, so this covers both.
    entities: list[SelectEntity] = [
        ClockModeSelect(coordinator=coordinator, thing_name=rest_device.thing_name)
        for rest_device in coordinator.rest_devices
        if isinstance(rest_device, RestoreV5)
    ]
    for rest_device in coordinator.rest_devices:
        if isinstance(rest_device, Restore):
            entities.append(
                RestoreRoutineStep(coordinator=coordinator, thing_name=rest_device.thing_name)
            )
            entities.append(
                RestoreClockMode(coordinator=coordinator, thing_name=rest_device.thing_name)
            )
    async_add_entities(entities)


class ClockModeSelect(HatchEntity, SelectEntity):
    """Clock mode select."""

    _attr_icon = "mdi:clock-time-four-outline"
    _attr_options: ClassVar[list[str]] = [MODE_ALWAYS_ON, MODE_OFF_AT_NIGHT, MODE_ALWAYS_OFF]

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the clock mode select."""
        super().__init__(
            coordinator=coordinator,
            thing_name=thing_name,
            entity_type="Clock Mode",
        )

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        dev = self.rest_device
        option = TURN_OFF_MODE_TO_OPTION.get(getattr(dev, "clock_turn_off_mode", None))
        if option is not None:
            return option
        # Fall back to the display flag until the mode field has been parsed.
        return MODE_ALWAYS_OFF if not dev.is_clock_on else MODE_ALWAYS_ON

    def select_option(self, option: str) -> None:
        """Select an option.

        Args:
            option: One of the clock mode options.
        """
        mode = OPTION_TO_TURN_OFF_MODE.get(option)
        if mode is not None:
            self.rest_device.set_clock_turn_off_mode(mode)
