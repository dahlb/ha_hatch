"""Tests for the favorite slots that keep scenes stable across Hatch app edits."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.ha_hatch.favorite_slots import (
    FavoriteSlots,
    favorite_id,
    favorite_name,
    favorite_scene_unique_id,
    favorite_scene_unique_id_prefix,
)

THING = "thing-1"


def _favorite(
    record_id: int, name: str = "Ocean", lineage_key: int | None = None, **extra: Any
) -> dict[str, Any]:
    """Build a favorite as Hatch's routine API returns it.

    Args:
        record_id: The record's id.
        name: The name of its first step.
        lineage_key: Its lineage key; None leaves it unset, as older favorites do.
        **extra: Further fields, such as ``displayOrder``.

    Returns:
        The favorite.
    """
    return {
        "id": record_id,
        "lineageKey": lineage_key,
        "steps": [{"name": name}],
        **extra,
    }


def _reconcile(slots: FavoriteSlots, *favorites: dict[str, Any]) -> dict[str, int]:
    """Reconcile and return each slot's favorite id.

    Args:
        slots: The slots.
        *favorites: The device's favorites, in display order.

    Returns:
        The favorite id by slot key, in display order.
    """
    by_slot, _ = slots.reconcile(THING, list(favorites))
    return {key: favorite["id"] for key, favorite in by_slot.items()}


def test_unique_id_matches_the_scenes_made_before_slots() -> None:
    """A slot's unique id is what HatchEntity built from ``Scene-{name}-{id}``."""
    assert favorite_scene_unique_id(THING, "White Noise-123") == "thing-1_scene-white_noise-123"
    assert favorite_scene_unique_id_prefix(THING) == "thing-1_scene-"


@pytest.mark.parametrize(
    ("favorite", "expected_id", "expected_name"),
    [
        (_favorite(5, "Rain"), 5, "Rain"),
        ({"id": "6", "steps": [{"name": "Rain"}]}, 6, "Rain"),
        ({"id": None, "steps": []}, None, None),
        ({"id": "x", "steps": [{"name": 3}]}, None, None),
        ({}, None, None),
        (None, None, None),
    ],
)
def test_favorite_id_and_name(
    favorite: Any, expected_id: int | None, expected_name: str | None
) -> None:
    """Ids and names are read defensively from favorites of any shape."""
    assert favorite_id(favorite) == expected_id
    assert favorite_name(favorite) == expected_name


def test_new_favorites_get_slots_keyed_by_name_and_id() -> None:
    """New favorites are keyed by their name and first seen id, in display order."""
    slots = FavoriteSlots()
    by_slot, changed = slots.reconcile(THING, [_favorite(2, "Rain"), _favorite(1)])

    assert changed
    assert list(by_slot) == ["Rain-2", "Ocean-1"]
    assert slots.name(THING, "Rain-2") == "Rain"


def test_unchanged_favorites_report_no_change() -> None:
    """Reconciling the same favorites again changes nothing."""
    slots = FavoriteSlots()
    slots.reconcile(THING, [_favorite(1)])

    _, changed = slots.reconcile(THING, [_favorite(1)])

    assert not changed


def test_an_edit_follows_the_lineage_key() -> None:
    """An edit that replaces the id, keeping the lineage key, keeps the slot."""
    slots = FavoriteSlots()
    _reconcile(slots, _favorite(313263808, "Night", 313263808))

    assert _reconcile(slots, _favorite(313265545, "Night", 313263808)) == {
        "Night-313263808": 313265545
    }
    assert _reconcile(slots, _favorite(313265980, "Night", 313263808)) == {
        "Night-313263808": 313265980
    }


def test_a_renamed_edit_follows_the_lineage_key() -> None:
    """The lineage key matches even when the favorite was renamed too."""
    slots = FavoriteSlots()
    _reconcile(slots, _favorite(10, "Night", 10))

    by_slot, _ = slots.reconcile(THING, [_favorite(11, "Sleep", 10)])

    assert list(by_slot) == ["Night-10"]
    assert slots.name(THING, "Night-10") == "Sleep"


def test_a_reorder_without_lineage_keys_follows_the_name() -> None:
    """Reordering replaces every id; favorites without lineage keys match by name."""
    slots = FavoriteSlots()
    _reconcile(slots, _favorite(1, "White Noise"), _favorite(2, "Rain", 2))

    assert _reconcile(slots, _favorite(4, "Rain", 2), _favorite(3, "White Noise")) == {
        "Rain-2": 4,
        "White Noise-1": 3,
    }


def test_same_named_favorites_match_by_position() -> None:
    """Between favorites sharing a name, the nearest in display order wins."""
    slots = FavoriteSlots()
    _reconcile(slots, _favorite(1), _favorite(2, "Rain"), _favorite(3))

    assert _reconcile(slots, _favorite(11), _favorite(12, "Rain"), _favorite(13)) == {
        "Ocean-1": 11,
        "Rain-2": 12,
        "Ocean-3": 13,
    }


def test_deleted_favorites_lose_their_slots() -> None:
    """A favorite with no match is dropped, and a device without any is forgotten."""
    slots = FavoriteSlots()
    _reconcile(slots, _favorite(1), _favorite(2, "Rain"))

    assert _reconcile(slots, _favorite(2, "Rain")) == {"Rain-2": 2}
    _, changed = slots.reconcile(THING, [])

    assert changed
    assert slots.as_dict() == {}


def test_a_new_favorite_beside_an_edit_gets_its_own_slot() -> None:
    """A new favorite is not mistaken for an edited one with a different name."""
    slots = FavoriteSlots()
    _reconcile(slots, _favorite(1, "Night", 1))

    assert _reconcile(slots, _favorite(2, "Night", 1), _favorite(3, "Rain", 3)) == {
        "Night-1": 2,
        "Rain-3": 3,
    }


def test_a_new_slot_does_not_reuse_a_taken_key() -> None:
    """A new favorite whose natural key is taken gets a distinct one."""
    slots = FavoriteSlots({THING: {"Ocean-1": {"favorite_id": 9, "name": "Other", "order": 0}}})

    assert _reconcile(slots, _favorite(9, "Other"), _favorite(1)) == {
        "Ocean-1": 9,
        "Ocean-1_": 1,
    }


def test_unusable_and_duplicate_favorites_are_skipped() -> None:
    """Favorites without an id or name are skipped, and a repeated id counts once."""
    slots = FavoriteSlots()

    assert _reconcile(
        slots,
        {"id": None, "steps": [{"name": "Broken"}]},
        {"id": 5, "steps": []},
        "not a favorite",  # type: ignore[arg-type]
        _favorite(1),
        _favorite(1, "Copy"),
    ) == {"Ocean-1": 1}


def test_state_round_trips() -> None:
    """Saved state restores the same slots, and as_dict returns a copy."""
    slots = FavoriteSlots()
    _reconcile(slots, _favorite(1, "Night", 1))
    saved = slots.as_dict()
    saved[THING]["Night-1"]["name"] = "changed"

    restored = FavoriteSlots(slots.as_dict())

    assert _reconcile(restored, _favorite(2, "Night", 1)) == {"Night-1": 2}
    assert slots.name(THING, "Night-1") == "Night"
    assert restored.name(THING, "missing") is None
    assert restored.slots("other") == {}
