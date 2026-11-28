"""Tests for the Hatch services."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import pytest

from custom_components.ha_hatch import services
from custom_components.ha_hatch.const import DOMAIN

from .conftest import RESTORE_THING, RestoreFixture


def _registry_with(unique_id: str, platform: str = DOMAIN) -> MagicMock:
    """Return an entity registry holding one entry.

    Args:
        unique_id: The entry's unique id.
        platform: The entry's integration.

    Returns:
        The mocked registry.
    """
    registry = MagicMock()
    registry.async_get.return_value = SimpleNamespace(
        platform=platform, unique_id=unique_id, config_entry_id="entry-1"
    )
    return registry


def _hass_with(coordinator: Any, state: ConfigEntryState = ConfigEntryState.LOADED) -> Any:
    """Return a hass whose only config entry, ``entry-1``, is a Hatch account.

    Args:
        coordinator: The entry's coordinator.
        state: The entry's state.

    Returns:
        The stub hass.
    """
    entry = SimpleNamespace(domain=DOMAIN, state=state, runtime_data=coordinator)
    entries = {"entry-1": entry}
    return SimpleNamespace(config_entries=SimpleNamespace(async_get_entry=entries.get))


@pytest.mark.parametrize("suffix", ["switch", "time", "repeat"])
def test_any_restore_alarm_entity_identifies_its_alarm(
    restore: RestoreFixture, suffix: str
) -> None:
    """Each of an original Restore alarm's entities resolves to its device and slot."""
    target = services._alarm_target_from_entity_id(
        _hass_with(restore.coordinator),
        _registry_with(f"{RESTORE_THING}_restore_alarm_1002_{suffix}"),
        "time.bedroom_alarm_1_wake_time",
        raise_if_not_alarm=True,
    )

    assert target == ((RESTORE_THING, "1002"), (restore.coordinator, restore.device, "1002"))


@pytest.mark.parametrize("state", [ConfigEntryState.NOT_LOADED, ConfigEntryState.SETUP_RETRY])
def test_an_alarm_of_an_account_that_is_not_loaded_is_rejected(
    restore: RestoreFixture, state: ConfigEntryState
) -> None:
    """The alarm's own config entry must be loaded for the service to reach it."""
    with pytest.raises(ServiceValidationError, match="not loaded"):
        services._alarm_target_from_entity_id(
            _hass_with(restore.coordinator, state),
            _registry_with(f"{RESTORE_THING}_restore_alarm_1002_switch"),
            "switch.bedroom_alarm_1",
            raise_if_not_alarm=True,
        )


def test_other_restore_entities_are_not_alarms(restore: RestoreFixture) -> None:
    """The Restore's other entities are rejected as targets."""
    with pytest.raises(ServiceValidationError):
        services._alarm_target_from_entity_id(
            _hass_with(restore.coordinator),
            _registry_with(f"{RESTORE_THING}_light"),
            "light.bedroom_light",
            raise_if_not_alarm=True,
        )


async def test_restore_weekdays_go_through_the_coordinator(restore: RestoreFixture) -> None:
    """Weekdays for an original Restore alarm are saved through its slot."""
    restore.coordinator.restore_alarms_by_slot(restore.device)
    hass = SimpleNamespace()
    call = SimpleNamespace(data={services.ATTR_WEEKDAYS: ["saturday", "sunday"]})

    with (
        patch.object(
            services,
            "_alarm_targets_from_service_call",
            return_value={(RESTORE_THING, "1002"): (restore.coordinator, restore.device, "1002")},
        ),
    ):
        await services._async_set_alarm_weekdays(hass, call)

    assert restore.coordinator.restore_alarm(restore.device, "1002")["daysOfWeek"] == 65


async def test_other_alarms_still_use_the_device(restore: RestoreFixture) -> None:
    """Scheduled-routine alarms keep calling the device's own method."""
    other = SimpleNamespace(device_name="Rest", set_alarm_weekdays=AsyncMock())
    hass = SimpleNamespace()
    call = SimpleNamespace(data={services.ATTR_WEEKDAYS: ["monday"]})

    with (
        patch.object(
            services,
            "_alarm_targets_from_service_call",
            return_value={("thing-rest", "7"): (restore.coordinator, other, "7")},
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
    hass = SimpleNamespace()
    call = SimpleNamespace(data={services.ATTR_WEEKDAYS: ["monday"]})

    with (
        patch.object(
            services,
            "_alarm_targets_from_service_call",
            return_value={("thing-rest", "7"): (restore.coordinator, other, "7")},
        ),
        pytest.raises(HomeAssistantError) as raised,
    ):
        await services._async_set_alarm_weekdays(
            cast("HomeAssistant", hass), cast("ServiceCall", call)
        )

    assert raised.value.translation_placeholders == {"target": "Rest"}
    assert raised.value.__cause__ is error
