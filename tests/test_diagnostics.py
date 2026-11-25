"""Tests for the Hatch diagnostics."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from custom_components.ha_hatch import diagnostics
from custom_components.ha_hatch.const import DOMAIN

from .conftest import RESTORE_THING, RestoreFixture


async def test_carries_the_raw_shadow_without_headphone_secrets(restore: RestoreFixture) -> None:
    """An original Restore's raw shadow is included, minus its headphone pairing details."""
    device_registry = MagicMock()
    device_registry.async_get_device.return_value = None
    hass = SimpleNamespace(data={DOMAIN: restore.coordinator})
    config_entry = MagicMock()
    config_entry.as_dict.return_value = {"data": {}}

    with (
        patch.object(diagnostics.dr, "async_get", return_value=device_registry),
        patch.object(diagnostics.er, "async_get", return_value=MagicMock()),
    ):
        data = await diagnostics.async_get_config_entry_diagnostics(hass, config_entry)

    shadow = data[RESTORE_THING]["shadow_state"]
    assert shadow["content"]["routineId"] == 501
    assert shadow["headphones"]["stateResult"] == "unknown"
    assert shadow["headphones"]["requestedPin"] == "**REDACTED**"
    assert shadow["headphones"]["connectedMacAddress"] == "**REDACTED**"
    # Redacting a copy: the device keeps its real state.
    assert restore.device.shadow_state["headphones"]["requestedPin"] == "1234"
