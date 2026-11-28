"""Tests for the Hatch time entities."""

from datetime import time
from unittest.mock import MagicMock

from hatch_rest_api import RestoreV5
import pytest

from custom_components.ha_hatch.time import CLOCK_SCHEDULE_TIMES, HatchClockScheduleTime

from .conftest import run_commands_on_mock


def _clock_schedule_time(
    rest_device: MagicMock, entity_type: str, attr: str, setter: str, icon: str
) -> HatchClockScheduleTime:
    """Build a clock schedule time backed by a mocked coordinator and device.

    Args:
        rest_device: Mocked Hatch device returned by the coordinator.
        entity_type: Entity type name.
        attr: Device attribute holding the current time string.
        setter: Name of the library setter used to write the time.
        icon: Entity icon.

    Returns:
        The clock schedule time entity under test.
    """
    run_commands_on_mock(rest_device)
    rest_device.device_name = "Restore"
    rest_device.mac = "AA:BB:CC:DD:EE:FF"
    rest_device.firmware_version = "1.0"
    coordinator = MagicMock()
    coordinator.rest_device_by_thing_name.return_value = rest_device
    return HatchClockScheduleTime(
        coordinator=coordinator,
        thing_name="thing",
        entity_type=entity_type,
        attr=attr,
        setter=setter,
        icon=icon,
    )


@pytest.mark.parametrize(
    ("entity_type", "attr", "setter", "icon"),
    CLOCK_SCHEDULE_TIMES,
)
async def test_set_value_calls_public_setter(
    entity_type: str, attr: str, setter: str, icon: str
) -> None:
    """Setting the time calls the matching public library setter."""
    rest_device = MagicMock(spec=RestoreV5)
    entity = _clock_schedule_time(rest_device, entity_type, attr, setter, icon)
    await entity.async_set_value(time(6, 30))
    getattr(rest_device, setter).assert_called_once_with(time(6, 30))
    rest_device._update.assert_not_called()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("06:30", time(6, 30)), ("19:45:15", time(19, 45, 15)), (None, None), ("bad", None)],
)
def test_native_value_parses_device_time(value: str | None, expected: time | None) -> None:
    """The device's clock time string is parsed into a time."""
    rest_device = MagicMock(spec=RestoreV5)
    rest_device.clock_turn_on_at = value
    entity = _clock_schedule_time(rest_device, *CLOCK_SCHEDULE_TIMES[0])
    assert entity.native_value == expected
