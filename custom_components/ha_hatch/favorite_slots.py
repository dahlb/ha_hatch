"""Stable identities for the favorites (Touch Ring presets) of Hatch devices.

Hatch gives a favorite or schedule a new record id every time it is edited
in the app (volume, brightness, color, sound, duration, start time, ...), and
reordering the Touch Ring replaces the ids of every record on that device.
Scenes keyed on the Hatch id would be replaced on every edit, breaking the
dashboards and automations that use them. Instead each favorite gets a slot,
created once and kept for as long as the favorite exists:

- a favorite whose id is unchanged keeps its slot;
- otherwise a vanished slot is matched to a new record with the same
  ``lineageKey``, which Hatch keeps across edits;
- failing that, to a new record with the same name; older favorites can have
  no ``lineageKey`` at all;
- a favorite with no match gets a new slot, and a slot with none is dropped.

A new slot is keyed ``{name}-{id}`` from the record it first sees, which is
the identity scenes used before slots existed, so existing scenes keep their
unique ids. No Home Assistant imports, so the logic can be tested on its own.
The state is a plain dict the integration persists across restarts.
"""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

FAVORITE_SCENE_UNIQUE_ID_MARKER = "_scene-"


def favorite_scene_unique_id_prefix(thing_name: str) -> str:
    """Return the prefix shared by the unique ids of a device's favorite scenes.

    Args:
        thing_name: The device's AWS IoT thing name.

    Returns:
        The prefix.
    """
    return f"{thing_name}{FAVORITE_SCENE_UNIQUE_ID_MARKER}"


def favorite_scene_unique_id(thing_name: str, slot_key: str) -> str:
    """Return the unique id of a favorite slot's scene.

    Matches what ``HatchEntity`` builds from an entity type of
    ``Scene-{slot_key}``, so scenes created before slots existed keep theirs.

    Args:
        thing_name: The device's AWS IoT thing name.
        slot_key: The favorite's slot.

    Returns:
        The unique id.
    """
    return f"{favorite_scene_unique_id_prefix(thing_name)}{slot_key.lower().replace(' ', '_')}"


def favorite_id(favorite: Any) -> int | None:
    """Return a favorite's Hatch record id, or None if it has no usable one.

    Args:
        favorite: A favorite from Hatch's routine API.

    Returns:
        The id, or None.
    """
    try:
        return int(favorite["id"])
    except KeyError, TypeError, ValueError:
        return None


def favorite_name(favorite: Any) -> str | None:
    """Return a favorite's name, the name of its first step.

    Args:
        favorite: A favorite from Hatch's routine API.

    Returns:
        The name, or None if the favorite has no named first step.
    """
    try:
        name = favorite["steps"][0]["name"]
    except KeyError, TypeError, IndexError:
        return None
    return name if isinstance(name, str) else None


def _lineage_key(favorite: dict[str, Any]) -> int | None:
    """Return a favorite's lineage key, which Hatch keeps across edits.

    Args:
        favorite: A favorite from Hatch's routine API.

    Returns:
        The lineage key, or None if it has none.
    """
    try:
        return int(favorite["lineageKey"])
    except KeyError, TypeError, ValueError:
        return None


def _slot_record(favorite: dict[str, Any], order: int) -> dict[str, Any]:
    """Return what a slot remembers of its favorite, to recognize it later.

    Args:
        favorite: The favorite in the slot.
        order: Its position in the device's favorites.

    Returns:
        Its id, lineage key, name and position.
    """
    return {
        "favorite_id": favorite_id(favorite),
        "lineage_key": _lineage_key(favorite),
        "name": favorite_name(favorite),
        "order": order,
    }


class FavoriteSlots:
    """Slot bookkeeping for the favorites of every device on one config entry.

    State: {thing_name: {slot_key: {"favorite_id": int, "lineage_key": int |
    None, "name": str, "order": int}}}.
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Start from saved state, or from nothing.

        Args:
            data: State saved by ``as_dict``.
        """
        self._things: dict[str, dict[str, dict[str, Any]]] = deepcopy(data or {})

    def as_dict(self) -> dict[str, Any]:
        """Return the state, to save.

        Returns:
            A copy of the state.
        """
        return deepcopy(self._things)

    def slots(self, thing_name: str) -> dict[str, dict[str, Any]]:
        """Return a device's slots by slot key.

        Args:
            thing_name: The device's AWS IoT thing name.

        Returns:
            The slots; empty for an unknown device.
        """
        return self._things.get(thing_name, {})

    def name(self, thing_name: str, slot_key: str) -> str | None:
        """Return the last known name of the favorite in a slot.

        Args:
            thing_name: The device's AWS IoT thing name.
            slot_key: The slot.

        Returns:
            The name, or None for an unknown slot.
        """
        slot = self.slots(thing_name).get(slot_key)
        return slot.get("name") if slot else None

    def reconcile(
        self, thing_name: str, favorites: Iterable[Any]
    ) -> tuple[dict[str, dict[str, Any]], bool]:
        """Give every favorite a slot.

        Args:
            thing_name: The device's AWS IoT thing name.
            favorites: The device's current favorites, in display order.

        Returns:
            The favorites by slot key, in display order, and whether the
            stored state changed.
        """
        before = deepcopy(self._things.get(thing_name))
        slots = self._things.setdefault(thing_name, {})

        # Usable favorites by id, keeping the first of any duplicate id.
        by_id: dict[int, dict[str, Any]] = {}
        for favorite in favorites:
            if (
                isinstance(favorite, dict)
                and (record_id := favorite_id(favorite)) is not None
                and favorite_name(favorite) is not None
            ):
                by_id.setdefault(record_id, favorite)
        order = {record_id: index for index, record_id in enumerate(by_id)}

        claimed: dict[str, int] = {
            key: slot["favorite_id"] for key, slot in slots.items() if slot["favorite_id"] in by_id
        }

        def unclaimed() -> list[int]:
            """Return the ids no slot holds yet, in display order.

            Returns:
                The ids.
            """
            taken = set(claimed.values())
            return [record_id for record_id in by_id if record_id not in taken]

        def orphans() -> list[str]:
            """Return the slots whose favorite is gone, in their last known order.

            Returns:
                The slot keys.
            """
            return sorted(
                (key for key in slots if key not in claimed),
                key=lambda key: (slots[key].get("order", 0), key),
            )

        # An edited favorite keeps its lineage key.
        for key in orphans():
            lineage_key = slots[key].get("lineage_key")
            if lineage_key is None:
                continue
            match = next(
                (
                    record_id
                    for record_id in unclaimed()
                    if _lineage_key(by_id[record_id]) == lineage_key
                ),
                None,
            )
            if match is not None:
                claimed[key] = match

        # Without one, fall back to the name; between favorites sharing a
        # name, the one nearest the slot's last position wins.
        candidates = sorted(
            (
                abs(order[record_id] - slots[key].get("order", 0)),
                slots[key].get("order", 0),
                order[record_id],
                key,
                record_id,
            )
            for key in orphans()
            for record_id in unclaimed()
            if slots[key].get("name") == favorite_name(by_id[record_id])
        )
        for _, _, _, key, record_id in candidates:
            if key in claimed or record_id in claimed.values():
                continue
            claimed[key] = record_id

        for key in [key for key in slots if key not in claimed]:
            del slots[key]

        # Favorites still without a slot are new.
        for record_id in unclaimed():
            key = f"{favorite_name(by_id[record_id])}-{record_id}"
            while key in slots:
                key += "_"
            slots[key] = {}
            claimed[key] = record_id

        for key, record_id in claimed.items():
            slots[key] = _slot_record(by_id[record_id], order[record_id])

        if not slots:
            self._things.pop(thing_name, None)
        changed = before != self._things.get(thing_name)
        return (
            {
                key: by_id[record_id]
                for key, record_id in sorted(claimed.items(), key=lambda item: order[item[1]])
            },
            changed,
        )
