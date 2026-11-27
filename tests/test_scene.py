"""Tests for the favorite scenes, which keep their identity across Hatch app edits."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

from hatch_rest_api import RestIot
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pytest

from custom_components.ha_hatch import scene
from custom_components.ha_hatch.const import CONFIG_NUMBERED_PRESET_SCENES, DOMAIN

from .conftest import FakeCoordinator, StubShadowClient, build_device

THING = "thing-rest"
MAC = "AA:BB:CC:DD:EE:01"


def _favorite(record_id: int, name: str, lineage_key: int | None = None) -> dict[str, Any]:
    """Build a favorite as Hatch's routine API returns it.

    Args:
        record_id: The record's id.
        name: The name of its first step.
        lineage_key: Its lineage key, or None.

    Returns:
        The favorite.
    """
    return {
        "id": record_id,
        "lineageKey": lineage_key,
        "displayOrder": record_id,
        "steps": [{"name": name}],
    }


class SceneHarness:
    """A Rest 2nd gen device, a coordinator serving it and its scene platform."""

    def __init__(self, favorites: list[dict[str, Any]], numbered: bool = False) -> None:
        """Build the device with ``favorites``.

        Args:
            favorites: The device's favorites.
            numbered: Whether scene names carry the preset number.
        """
        device, client = build_device(RestIot, THING, MAC)
        device.favorites = favorites
        self.device: RestIot = device
        self.client: StubShadowClient = client
        self.coordinator = FakeCoordinator([device])
        self.hass = MagicMock()
        self.hass.data = {DOMAIN: self.coordinator}
        self.hass.async_add_executor_job = AsyncMock(
            side_effect=lambda function, *args: function(*args)
        )
        self.config_entry = SimpleNamespace(
            options={CONFIG_NUMBERED_PRESET_SCENES: numbered},
            entry_id="entry-1",
            async_on_unload=lambda remove: None,
        )
        self.added: list[scene.RiotScene] = []
        self.registry = MagicMock()
        self.registry_entries: list[Any] = []

    def _patches(self) -> tuple[Any, Any]:
        """Patch the entity registry the platform prunes.

        Returns:
            The patchers.
        """
        return (
            patch.object(scene.er, "async_get", return_value=self.registry),
            patch.object(
                scene.er,
                "async_entries_for_config_entry",
                side_effect=lambda registry, entry_id: self.registry_entries,
            ),
        )

    def _add(self, entities: list[scene.RiotScene]) -> None:
        """Record added scenes and give them a hass, as the platform would.

        Args:
            entities: The scenes added.
        """
        for entity in entities:
            entity.hass = self.hass
            entity.async_remove = AsyncMock()  # type: ignore[method-assign,misc]
        self.added.extend(entities)

    async def set_up(self) -> None:
        """Run the platform's setup."""
        registry_get, registry_entries = self._patches()
        with registry_get, registry_entries:
            await scene.async_setup_entry(
                self.hass,
                cast(ConfigEntry, self.config_entry),
                cast(AddEntitiesCallback, self._add),
            )

    async def refresh(self, favorites: list[dict[str, Any]]) -> None:
        """Simulate a re-login that fetched ``favorites``.

        Args:
            favorites: The favorites Hatch now reports.
        """
        self.device.favorites = favorites
        registry_get, registry_entries = self._patches()
        with registry_get, registry_entries:
            await self.coordinator.async_run_alarm_refresh_callbacks()

    def scene(self, unique_id: str) -> scene.RiotScene:
        """Return the scene added under ``unique_id``.

        Args:
            unique_id: The unique id.

        Returns:
            The scene.
        """
        return next(entity for entity in self.added if entity.unique_id == unique_id)


def _registry_entry(unique_id: str, domain: str = "scene") -> SimpleNamespace:
    """Build an entity registry entry.

    Args:
        unique_id: Its unique id.
        domain: Its domain.

    Returns:
        The entry.
    """
    return SimpleNamespace(unique_id=unique_id, domain=domain, entity_id=f"{domain}.{unique_id}")


async def test_scenes_keep_their_legacy_unique_ids() -> None:
    """Scenes keep the ``Scene-{name}-{id}`` unique ids they had before slots."""
    harness = SceneHarness([_favorite(10, "White Noise"), _favorite(20, "Rain", 20)], True)

    await harness.set_up()

    assert [entity.unique_id for entity in harness.added] == [
        "thing-rest_scene-white_noise-10",
        "thing-rest_scene-rain-20",
    ]
    rain = harness.scene("thing-rest_scene-rain-20")
    assert rain.name == "Preset 2 - Rain"
    assert rain.available
    assert rain.extra_state_attributes == {
        "preset_number": 2,
        "hatch_favorite_id": 20,
        "hatch_display_order": 20,
    }


async def test_an_edited_favorite_keeps_its_scene_and_activates_its_new_id() -> None:
    """An app edit replaces the id; the scene stays and starts the new record."""
    harness = SceneHarness([_favorite(313263808, "Night", 313263808)])
    await harness.set_up()
    night = harness.added[0]

    await harness.refresh([_favorite(313268506, "Night", 313263808)])
    await night.async_activate()

    assert len(harness.added) == 1
    night.async_remove.assert_not_called()  # type: ignore[attr-defined]
    assert (night.extra_state_attributes or {})["hatch_favorite_id"] == 313268506
    assert harness.client.published[-1]["current"]["srId"] == 313268506


async def test_a_reorder_without_lineage_keys_keeps_the_scenes() -> None:
    """Reordering replaces every id; scenes follow by name and update their numbers."""
    harness = SceneHarness([_favorite(1, "White Noise"), _favorite(2, "Rain")], True)
    await harness.set_up()

    await harness.refresh([_favorite(4, "Rain"), _favorite(3, "White Noise")])

    assert len(harness.added) == 2
    assert harness.scene("thing-rest_scene-white_noise-1").name == "Preset 2 - White Noise"
    assert harness.scene("thing-rest_scene-rain-2").name == "Preset 1 - Rain"


async def test_added_and_deleted_favorites_are_reconciled() -> None:
    """New favorites get scenes; deleted ones lose theirs and their registrations."""
    harness = SceneHarness([_favorite(1, "Ocean"), _favorite(2, "Rain")])
    await harness.set_up()
    rain = harness.scene("thing-rest_scene-rain-2")
    harness.registry_entries = [
        _registry_entry("thing-rest_scene-ocean-1"),
        _registry_entry("thing-rest_scene-rain-2"),
        _registry_entry("thing-rest_scene-ocean-0"),
        _registry_entry("other-thing_scene-ocean-5"),
        _registry_entry("thing-rest_scene-light", domain="light"),
    ]

    await harness.refresh([_favorite(1, "Ocean"), _favorite(3, "Forest")])

    assert [entity.unique_id for entity in harness.added][-1] == "thing-rest_scene-forest-3"
    rain.async_remove.assert_awaited_once_with(force_remove=True)  # type: ignore[attr-defined]
    removed = [call.args[0] for call in harness.registry.async_remove.call_args_list]
    assert removed == ["scene.thing-rest_scene-rain-2", "scene.thing-rest_scene-ocean-0"]


async def test_a_deleted_favorite_scene_is_unavailable_and_cannot_activate() -> None:
    """A scene whose favorite is gone reports unavailable and refuses activation."""
    harness = SceneHarness([_favorite(1, "Ocean")])
    await harness.set_up()
    ocean = harness.added[0]
    harness.device.favorites = []

    assert not ocean.available
    assert ocean.name is None
    assert ocean.extra_state_attributes is None
    with pytest.raises(HomeAssistantError):
        await ocean.async_activate()


async def test_a_missing_device_leaves_the_scene_unavailable() -> None:
    """A scene whose device disappeared keeps its last known name."""
    harness = SceneHarness([_favorite(1, "Ocean")])
    await harness.set_up()
    ocean = harness.added[0]
    harness.coordinator.rest_devices = []

    assert not ocean.available
    assert ocean.name == "Ocean"


@pytest.mark.parametrize(
    "favorites",
    [[], [{"id": 1, "steps": []}], [{"name": "no id"}]],
)
async def test_devices_without_usable_favorites_get_no_scenes(
    favorites: list[dict[str, Any]],
) -> None:
    """Favorites without an id or a named step are skipped."""
    harness = SceneHarness(favorites)

    await harness.set_up()

    assert harness.added == []


async def test_devices_without_a_favorites_list_are_left_alone() -> None:
    """A device without a favorites list gets no scenes and keeps its registrations."""
    harness = SceneHarness([])
    harness.device.favorites = None  # type: ignore[assignment]
    harness.registry_entries = [_registry_entry("thing-rest_scene-ocean-1")]

    await harness.set_up()

    assert harness.added == []
    harness.registry.async_remove.assert_not_called()


async def test_reconcile_runs_after_each_refresh() -> None:
    """The platform registers its reconciler with the coordinator."""
    harness = SceneHarness([_favorite(1, "Ocean")])
    callbacks: list[Callable[[], Any]] = harness.coordinator.alarm_refresh_callbacks

    await harness.set_up()

    assert len(callbacks) == 1
