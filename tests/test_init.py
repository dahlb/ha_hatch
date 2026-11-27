"""Tests for the Hatch integration setup."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import custom_components.ha_hatch as integration


async def test_removing_an_entry_drops_its_stored_slots() -> None:
    """Removing the config entry removes its stored alarm and favorite slots."""
    store = MagicMock()
    store.async_remove = AsyncMock()

    with patch.object(integration, "Store", return_value=store) as store_class:
        await integration.async_remove_entry(MagicMock(), SimpleNamespace(entry_id="entry-1"))

    assert [call.args[2] for call in store_class.call_args_list] == [
        "ha_hatch.restore_alarm_slots.entry-1",
        "ha_hatch.favorite_slots.entry-1",
    ]
    assert store.async_remove.await_count == 2
