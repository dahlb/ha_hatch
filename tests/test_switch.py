"""Tests for the Hatch switch entities."""

from unittest.mock import MagicMock

import pytest

from custom_components.ha_hatch.switch import HatchClockTapSwitch


def _clock_tap_switch(rest_device: MagicMock) -> HatchClockTapSwitch:
    """Build a clock tap switch backed by a mocked coordinator and device.

    Args:
        rest_device: Mocked Hatch device returned by the coordinator.

    Returns:
        The clock tap switch entity under test.
    """
    rest_device.device_name = "Restore"
    rest_device.mac = "AA:BB:CC:DD:EE:FF"
    rest_device.firmware_version = "1.0"
    coordinator = MagicMock()
    coordinator.rest_device_by_thing_name.return_value = rest_device
    return HatchClockTapSwitch(coordinator=coordinator, thing_name="thing")


@pytest.mark.parametrize("value", [True, False, None])
def test_clock_tap_switch_is_on_uses_device_property(value: bool | None) -> None:
    """The switch state mirrors the device's is_clock_tap_on property."""
    rest_device = MagicMock()
    rest_device.is_clock_tap_on = value
    assert _clock_tap_switch(rest_device).is_on is value


def test_clock_tap_switch_turn_on_calls_device_method() -> None:
    """Turning the switch on calls clock_tap_on on the device."""
    rest_device = MagicMock()
    _clock_tap_switch(rest_device).turn_on()
    rest_device.clock_tap_on.assert_called_once_with()
    rest_device.clock_tap_off.assert_not_called()


def test_clock_tap_switch_turn_off_calls_device_method() -> None:
    """Turning the switch off calls clock_tap_off on the device."""
    rest_device = MagicMock()
    _clock_tap_switch(rest_device).turn_off()
    rest_device.clock_tap_off.assert_called_once_with()
    rest_device.clock_tap_on.assert_not_called()
