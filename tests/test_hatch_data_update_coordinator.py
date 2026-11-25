"""Tests for the coordinator's original Restore alarm slots."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ha_hatch import hatch_data_update_coordinator as coordinator_module
from custom_components.ha_hatch.hatch_data_update_coordinator import (
    RESTORE_ALARM_SLOTS_SAVE_DELAY,
    HatchDataUpdateCoordinator,
    restore_alarm_slots_store_key,
)

from .conftest import RESTORE_THING, RestoreFixture, build_restore


def test_store_key_is_per_entry() -> None:
    """Each config entry stores its slots under its own key."""
    assert restore_alarm_slots_store_key("entry-1") == "ha_hatch.restore_alarm_slots.entry-1"


async def test_load_reads_the_saved_slots() -> None:
    """Saved slots are loaded from the entry's store."""
    store = MagicMock()
    store.async_load = AsyncMock(
        return_value={RESTORE_THING: {"1002": {"number": 1, "alarm_id": 5000}}}
    )
    coordinator = SimpleNamespace(hass=MagicMock(), config_entry=SimpleNamespace(entry_id="e1"))

    with patch.object(coordinator_module, "Store", return_value=store) as store_class:
        await HatchDataUpdateCoordinator.async_load_restore_alarm_slots(coordinator)

    assert store_class.call_args.args[2] == "ha_hatch.restore_alarm_slots.e1"
    assert coordinator.restore_alarm_slots.alarm_id(RESTORE_THING, "1002") == 5000


async def test_load_without_an_entry_keeps_slots_in_memory() -> None:
    """Without a config entry nothing is loaded or stored."""
    coordinator = SimpleNamespace(config_entry=None, _restore_alarm_slots_store=None)

    with patch.object(coordinator_module, "Store") as store_class:
        await HatchDataUpdateCoordinator.async_load_restore_alarm_slots(coordinator)

    store_class.assert_not_called()


def test_new_slots_are_saved(restore: RestoreFixture) -> None:
    """Slots that change are queued for saving."""
    store = MagicMock()
    restore.coordinator._restore_alarm_slots_store = store

    restore.coordinator.restore_alarms_by_slot(restore.device)

    store.async_delay_save.assert_called_once()
    assert store.async_delay_save.call_args.args[1] == RESTORE_ALARM_SLOTS_SAVE_DELAY


def test_no_slots_until_the_alarms_load() -> None:
    """A device whose alarms have not loaded has no slots yet."""
    restore = build_restore(alarms_loaded=False)
    assert restore.coordinator.restore_alarms_by_slot(restore.device) == {}
    assert restore.coordinator.restore_alarm(None, "1002") is None


async def test_an_empty_slot_cannot_be_changed(restore: RestoreFixture) -> None:
    """Changing an alarm in an empty slot fails."""
    with pytest.raises(ValueError):
        await restore.coordinator.async_set_restore_alarm_enabled(restore.device, "404", True)
