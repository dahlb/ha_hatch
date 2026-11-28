"""Tests for the Hatch select entities."""

from unittest.mock import MagicMock

import pytest

from custom_components.ha_hatch.select import (
    MODE_ALWAYS_OFF,
    MODE_ALWAYS_ON,
    MODE_OFF_AT_NIGHT,
    ClockModeSelect,
)

from .conftest import run_commands_on_mock


def _clock_mode_select(rest_device: MagicMock) -> ClockModeSelect:
    """Build a clock mode select backed by a mocked coordinator and device.

    Args:
        rest_device: Mocked Hatch device returned by the coordinator.

    Returns:
        The clock mode select entity under test.
    """
    run_commands_on_mock(rest_device)
    rest_device.device_name = "Restore"
    rest_device.mac = "AA:BB:CC:DD:EE:FF"
    rest_device.firmware_version = "1.0"
    coordinator = MagicMock()
    coordinator.rest_device_by_thing_name.return_value = rest_device
    return ClockModeSelect(coordinator=coordinator, thing_name="thing")


@pytest.mark.parametrize(
    ("option", "mode"),
    [
        (MODE_ALWAYS_ON, "never"),
        (MODE_OFF_AT_NIGHT, "custom"),
        (MODE_ALWAYS_OFF, "always"),
    ],
)
async def test_select_option_calls_device_method(option: str, mode: str) -> None:
    """Selecting an option calls set_clock_turn_off_mode with the matching mode."""
    rest_device = MagicMock()
    await _clock_mode_select(rest_device).async_select_option(option)
    rest_device.set_clock_turn_off_mode.assert_called_once_with(mode)
    rest_device._update.assert_not_called()


async def test_select_unknown_option_does_nothing() -> None:
    """An unknown option sends nothing to the device."""
    rest_device = MagicMock()
    await _clock_mode_select(rest_device).async_select_option("bogus")
    rest_device.set_clock_turn_off_mode.assert_not_called()


@pytest.mark.parametrize(
    ("mode", "option"),
    [
        ("never", MODE_ALWAYS_ON),
        ("custom", MODE_OFF_AT_NIGHT),
        ("always", MODE_ALWAYS_OFF),
    ],
)
def test_current_option_from_turn_off_mode(mode: str, option: str) -> None:
    """The current option mirrors the device's clock_turn_off_mode."""
    rest_device = MagicMock()
    rest_device.clock_turn_off_mode = mode
    assert _clock_mode_select(rest_device).current_option == option


@pytest.mark.parametrize(
    ("is_clock_on", "option"), [(True, MODE_ALWAYS_ON), (False, MODE_ALWAYS_OFF)]
)
def test_current_option_falls_back_to_clock_flag(is_clock_on: bool, option: str) -> None:
    """Without a turn-off mode, the current option follows is_clock_on."""
    rest_device = MagicMock()
    rest_device.clock_turn_off_mode = None
    rest_device.is_clock_on = is_clock_on
    assert _clock_mode_select(rest_device).current_option == option
