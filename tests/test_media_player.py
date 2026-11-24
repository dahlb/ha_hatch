"""Tests for the Hatch media player platform."""

from __future__ import annotations

from hatch_rest_api import RestMini

from custom_components.ha_hatch import media_player
from custom_components.ha_hatch.media_rest_entity import MediaRestEntity
from custom_components.ha_hatch.restore_entities import RestoreSound

from .conftest import RestoreFixture, build_device


def test_restore_gets_its_own_media_player(restore: RestoreFixture) -> None:
    """The original Restore gets RestoreSound, not the Rest Mini/Plus fallback."""
    rest_mini, _ = build_device(RestMini, "thing-mini", "AA:BB:CC:DD:EE:FF")
    coordinator = restore.coordinator
    coordinator.rest_devices.append(rest_mini)

    assert isinstance(
        media_player.choose_media_entity(
            restore.device, config_turn_on_media=True, coordinator=coordinator
        ),
        RestoreSound,
    )
    # The models that do fall through still get the Rest Mini/Plus player.
    assert isinstance(
        media_player.choose_media_entity(
            rest_mini, config_turn_on_media=True, coordinator=coordinator
        ),
        MediaRestEntity,
    )
