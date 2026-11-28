"""Tests for the coordinator's original Restore alarm slots."""

from __future__ import annotations

from concurrent.futures import Future
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

from hatch_rest_api import RestIot, RestoreV5
import pytest

from custom_components.ha_hatch import hatch_data_update_coordinator as coordinator_module
from custom_components.ha_hatch.favorite_slots import FavoriteSlots
from custom_components.ha_hatch.hatch_data_update_coordinator import (
    FAVORITE_SLOTS_SAVE_DELAY,
    RESTORE_ALARM_SLOTS_SAVE_DELAY,
    HatchDataUpdateCoordinator,
    favorite_slots_store_key,
    restore_alarm_slots_store_key,
)

from .conftest import RESTORE_THING, RestoreFixture, build_device, build_restore


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


def test_favorite_store_key_is_per_entry() -> None:
    """Each config entry stores its favorite slots under its own key."""
    assert favorite_slots_store_key("entry-1") == "ha_hatch.favorite_slots.entry-1"


async def test_load_reads_the_saved_favorite_slots() -> None:
    """Saved favorite slots are loaded from the entry's store."""
    store = MagicMock()
    store.async_load = AsyncMock(
        return_value={"thing": {"Ocean-1": {"favorite_id": 2, "name": "Ocean", "order": 0}}}
    )
    coordinator = SimpleNamespace(hass=MagicMock(), config_entry=SimpleNamespace(entry_id="e1"))

    with patch.object(coordinator_module, "Store", return_value=store) as store_class:
        await HatchDataUpdateCoordinator.async_load_favorite_slots(
            cast("HatchDataUpdateCoordinator", coordinator)
        )

    assert store_class.call_args.args[2] == "ha_hatch.favorite_slots.e1"
    assert coordinator.favorite_slots.name("thing", "Ocean-1") == "Ocean"


async def test_load_favorite_slots_without_an_entry_keeps_them_in_memory() -> None:
    """Without a config entry no favorite slots are loaded or stored."""
    coordinator = SimpleNamespace(config_entry=None, _favorite_slots_store=None)

    with patch.object(coordinator_module, "Store") as store_class:
        await HatchDataUpdateCoordinator.async_load_favorite_slots(
            cast("HatchDataUpdateCoordinator", coordinator)
        )

    store_class.assert_not_called()


def _favorite_coordinator(store: MagicMock | None) -> HatchDataUpdateCoordinator:
    """Build a stand-in coordinator for the favorite slot methods.

    Args:
        store: The favorite slots store, or None before loading.

    Returns:
        The coordinator.
    """
    return cast(
        "HatchDataUpdateCoordinator",
        SimpleNamespace(favorite_slots=FavoriteSlots(), _favorite_slots_store=store),
    )


@pytest.mark.parametrize("favorites", [None, "not a list"])
def test_favorites_by_slot_ignores_devices_without_favorites(favorites: object) -> None:
    """A device without a favorites list has no favorite slots."""
    coordinator = _favorite_coordinator(MagicMock())
    device = SimpleNamespace(thing_name="thing", favorites=favorites)

    assert HatchDataUpdateCoordinator.favorites_by_slot(coordinator, device) == {}
    cast("MagicMock", coordinator._favorite_slots_store).async_delay_save.assert_not_called()


@pytest.mark.parametrize("loaded", [True, False])
def test_favorites_by_slot_saves_only_changes(loaded: bool) -> None:
    """Changed favorite slots are queued for saving once loaded; unchanged ones are not."""
    store = MagicMock() if loaded else None
    coordinator = _favorite_coordinator(store)
    favorite = {"id": 7, "steps": [{"name": "Ocean"}]}
    device = SimpleNamespace(thing_name="thing", favorites=[favorite])

    assert HatchDataUpdateCoordinator.favorites_by_slot(coordinator, device) == {
        "Ocean-7": favorite
    }
    HatchDataUpdateCoordinator.favorites_by_slot(coordinator, device)

    if store is not None:
        store.async_delay_save.assert_called_once()
        assert store.async_delay_save.call_args.args[1] == FAVORITE_SLOTS_SAVE_DELAY


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


async def test_unsubscribe_releases_every_shadow_subscription_without_an_executor() -> None:
    """Teardown awaits async_unsubscribe on each device, with no executor job."""
    first, first_client = build_device(RestIot, "thing-1", "AA:BB:CC:DD:EE:01")
    second, second_client = build_device(RestoreV5, "thing-2", "AA:BB:CC:DD:EE:02")
    # No hass: an executor job would fail here.
    coordinator = cast("HatchDataUpdateCoordinator", SimpleNamespace(rest_devices=[first, second]))

    await HatchDataUpdateCoordinator._async_unsubscribe_shadows(coordinator)

    assert sorted(first_client.unsubscribed) == ["get-topic", "update-topic"]
    assert sorted(second_client.unsubscribed) == ["get-topic", "update-topic"]


async def test_unsubscribe_that_never_completes_is_cut_off() -> None:
    """An UNSUBACK that never arrives does not hold up the reconnect."""
    device, client = build_device(RestIot, "thing-1", "AA:BB:CC:DD:EE:01")
    client.unsubscribe = MagicMock(return_value=Future())  # type: ignore[method-assign]
    coordinator = cast("HatchDataUpdateCoordinator", SimpleNamespace(rest_devices=[device]))

    with patch.object(coordinator_module, "MQTT_UNSUBSCRIBE_TIMEOUT", 0.01):
        await HatchDataUpdateCoordinator._async_unsubscribe_shadows(coordinator)

    assert client.unsubscribe.call_count >= 1
