"""Tests for the Hatch media player platform."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from hatch_rest_api import RestIot, RestMini

from custom_components.ha_hatch import media_player
from custom_components.ha_hatch.custom_sounds import CUSTOM_SOUNDS_FILENAME
from custom_components.ha_hatch.media_rest_entity import MediaRestEntity
from custom_components.ha_hatch.media_riot_entity import MediaRiotEntity
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


async def test_setup_passes_custom_sounds_to_riot_players(tmp_path: Path) -> None:
    """Setup loads hatch_custom_sounds.yaml and offers it on riot media players."""
    rest_iot, _ = build_device(RestIot, "thing-iot", "AA:BB:CC:DD:EE:01")
    (tmp_path / CUSTOM_SOUNDS_FILENAME).write_text(
        "ClassicOcean:\n  id: 10165\n  wavUrl: https://example.com/ocean.wav\n",
        encoding="utf-8",
    )
    coordinator = MagicMock()
    coordinator.rest_devices = [rest_iot]
    coordinator.rest_device_by_thing_name.return_value = rest_iot
    hass = MagicMock()
    hass.config.path.side_effect = lambda name: str(tmp_path / name)

    async def run_in_executor(func: Any, *args: Any) -> Any:
        """Run the executor job inline.

        Args:
            func: Function to run.
            *args: Arguments for the function.

        Returns:
            The function's result.
        """
        return func(*args)

    hass.async_add_executor_job = run_in_executor
    config_entry = MagicMock()
    config_entry.options = {}
    config_entry.runtime_data = coordinator
    async_add_entities = MagicMock()

    await media_player.async_setup_entry(hass, config_entry, async_add_entities)

    (entities,), _ = async_add_entities.call_args
    assert isinstance(entities[0], MediaRiotEntity)
    assert "ClassicOcean" in (entities[0].sound_mode_list or [])
