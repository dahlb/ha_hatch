"""Tests for the Hatch services."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import pytest

from custom_components.ha_hatch import services
from custom_components.ha_hatch.const import DOMAIN

from .conftest import RESTORE_THING, FakeCoordinator, RestoreFixture


def _registry_with(unique_id: str, platform: str = DOMAIN) -> MagicMock:
    """Return an entity registry holding one entry.

    Args:
        unique_id: The entry's unique id.
        platform: The entry's integration.

    Returns:
        The mocked registry.
    """
    registry = MagicMock()
    registry.async_get.return_value = SimpleNamespace(platform=platform, unique_id=unique_id)
    return registry


@pytest.mark.parametrize("suffix", ["switch", "time", "repeat"])
def test_any_restore_alarm_entity_identifies_its_alarm(
    restore: RestoreFixture, suffix: str
) -> None:
    """Each of an original Restore alarm's entities resolves to its device and slot."""
    target = services._alarm_target_from_entity_id(
        _registry_with(f"{RESTORE_THING}_restore_alarm_1002_{suffix}"),
        restore.coordinator,
        "time.bedroom_alarm_1_wake_time",
        raise_if_not_alarm=True,
    )

    assert target == ((RESTORE_THING, "1002"), (restore.device, "1002"))


def test_other_restore_entities_are_not_alarms(restore: RestoreFixture) -> None:
    """The Restore's other entities are rejected as targets."""
    with pytest.raises(ServiceValidationError):
        services._alarm_target_from_entity_id(
            _registry_with(f"{RESTORE_THING}_light"),
            restore.coordinator,
            "light.bedroom_light",
            raise_if_not_alarm=True,
        )


async def test_restore_weekdays_go_through_the_coordinator(restore: RestoreFixture) -> None:
    """Weekdays for an original Restore alarm are saved through its slot."""
    restore.coordinator.restore_alarms_by_slot(restore.device)
    hass = SimpleNamespace(data={DOMAIN: restore.coordinator})
    call = SimpleNamespace(data={services.ATTR_WEEKDAYS: ["saturday", "sunday"]})

    with (
        patch.object(services, "HatchDataUpdateCoordinator", FakeCoordinator),
        patch.object(
            services,
            "_alarm_targets_from_service_call",
            return_value={(RESTORE_THING, "1002"): (restore.device, "1002")},
        ),
    ):
        await services._async_set_alarm_weekdays(hass, call)

    assert restore.coordinator.restore_alarm(restore.device, "1002")["daysOfWeek"] == 65


async def test_other_alarms_still_use_the_device(restore: RestoreFixture) -> None:
    """Scheduled-routine alarms keep calling the device's own method."""
    other = SimpleNamespace(device_name="Rest", set_alarm_weekdays=AsyncMock())
    hass = SimpleNamespace(data={DOMAIN: restore.coordinator})
    call = SimpleNamespace(data={services.ATTR_WEEKDAYS: ["monday"]})

    with (
        patch.object(services, "HatchDataUpdateCoordinator", FakeCoordinator),
        patch.object(
            services,
            "_alarm_targets_from_service_call",
            return_value={("thing-rest", "7"): (other, "7")},
        ),
    ):
        await services._async_set_alarm_weekdays(hass, call)

    other.set_alarm_weekdays.assert_awaited_once_with("7", ["monday"])


async def test_a_timed_out_alarm_edit_raises_a_home_assistant_error(
    restore: RestoreFixture,
) -> None:
    """A device that does not confirm the edit in time fails like any service."""
    error = TimeoutError()
    other = SimpleNamespace(device_name="Rest", set_alarm_weekdays=AsyncMock(side_effect=error))
    hass = SimpleNamespace(data={DOMAIN: restore.coordinator})
    call = SimpleNamespace(data={services.ATTR_WEEKDAYS: ["monday"]})

    with (
        patch.object(services, "HatchDataUpdateCoordinator", FakeCoordinator),
        patch.object(
            services,
            "_alarm_targets_from_service_call",
            return_value={("thing-rest", "7"): (other, "7")},
        ),
        pytest.raises(HomeAssistantError) as raised,
    ):
        await services._async_set_alarm_weekdays(
            cast("HomeAssistant", hass), cast("ServiceCall", call)
        )

    assert raised.value.translation_placeholders == {"target": "Rest"}
    assert raised.value.__cause__ is error
