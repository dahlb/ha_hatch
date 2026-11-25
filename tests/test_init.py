"""Tests for the Hatch integration setup."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import custom_components.ha_hatch as integration


async def test_removing_an_entry_drops_its_restore_alarm_slots() -> None:
    """Removing the config entry removes its stored alarm slots."""
    store = MagicMock()
    store.async_remove = AsyncMock()

    with patch.object(integration, "Store", return_value=store) as store_class:
        await integration.async_remove_entry(MagicMock(), SimpleNamespace(entry_id="entry-1"))

    assert store_class.call_args.args[2] == "ha_hatch.restore_alarm_slots.entry-1"
    store.async_remove.assert_awaited_once()
