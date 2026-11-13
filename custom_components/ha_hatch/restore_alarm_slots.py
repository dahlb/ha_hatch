"""Stable identities for the original Restore's alarms.

Hatch gives an original Restore's alarm a new id every time it is edited: the
app, and this integration, save an edit as a new copy and delete the original.
Entities keyed on the Hatch id would be replaced on every edit, breaking the
automations that use them. Instead each alarm gets a slot, numbered once
("Alarm 1", "Alarm 2", ...) and kept for as long as the alarm exists:

- an edit made here reports its old and new id, so its slot simply moves on;
- an edit made in the Hatch app shows up as one id gone and another new, so a
  vanished slot is matched to the new alarm that resembles it most;
- an alarm with no match gets a new slot, and a slot with none is dropped.

No Home Assistant imports, so the logic can be tested on its own. The state
is a plain dict the integration persists across restarts.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def alarm_signature(alarm: dict[str, Any]) -> dict[str, Any]:
    """What an alarm looks like, to recognize it after an edit elsewhere."""
    sound = alarm.get("sound") if isinstance(alarm.get("sound"), dict) else {}
    color = alarm.get("color") if isinstance(alarm.get("color"), dict) else {}
    alarm_time = str(alarm.get("time") or "")
    return {
        "time": alarm_time[-8:],
        "days": alarm.get("daysOfWeek"),
        "sound": sound.get("id"),
        "color": color.get("id"),
        "enabled": alarm.get("enabled"),
    }


def _similarity(previous: dict[str, Any], alarm: dict[str, Any]) -> int:
    current = alarm_signature(alarm)
    weights = {"time": 3, "days": 3, "sound": 1, "color": 1, "enabled": 1}
    return sum(
        weight
        for field, weight in weights.items()
        if previous.get(field) is not None and previous.get(field) == current.get(field)
    )


def _alarm_id(alarm: dict[str, Any]) -> int | None:
    try:
        return int(alarm["id"])
    except (KeyError, TypeError, ValueError):
        return None


class RestoreAlarmSlots:
    """Slot bookkeeping for every original Restore on one config entry.

    State: {thing_name: {slot_key: {"number": int, "alarm_id": int,
    "signature": {...}}}}.
    """

    def __init__(self, data: dict[str, Any] | None = None):
        self._things: dict[str, dict[str, dict[str, Any]]] = deepcopy(data or {})

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self._things)

    def slots(self, thing_name: str) -> dict[str, dict[str, Any]]:
        return self._things.get(thing_name, {})

    def alarm_id(self, thing_name: str, slot_key: str) -> int | None:
        slot = self.slots(thing_name).get(slot_key)
        return slot["alarm_id"] if slot else None

    def number(self, thing_name: str, slot_key: str) -> int | None:
        slot = self.slots(thing_name).get(slot_key)
        return slot["number"] if slot else None

    def replace(self, thing_name: str, old_alarm_id: int, new_alarm_id: int) -> bool:
        """Move a slot from an alarm to its edited copy. Returns whether it moved."""
        for slot in self.slots(thing_name).values():
            if slot["alarm_id"] == int(old_alarm_id):
                slot["alarm_id"] = int(new_alarm_id)
                return True
        return False

    def reconcile(self, thing_name: str, alarms: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], bool]:
        """Give every alarm a slot.

        Returns {slot_key: alarm} and whether the stored state changed.
        """
        before = deepcopy(self._things.get(thing_name))
        slots = self._things.setdefault(thing_name, {})
        by_id = {
            alarm_id: alarm
            for alarm in alarms
            if isinstance(alarm, dict) and (alarm_id := _alarm_id(alarm)) is not None
        }

        claimed = {key: slot["alarm_id"] for key, slot in slots.items() if slot["alarm_id"] in by_id}
        orphans = sorted(
            (key for key in slots if key not in claimed),
            key=lambda key: slots[key]["number"],
        )
        unclaimed = [alarm_id for alarm_id in sorted(by_id) if alarm_id not in claimed.values()]

        # Pair vanished slots with new alarms, most similar first.
        candidates = sorted(
            (-_similarity(slots[key].get("signature", {}), by_id[alarm_id]), slots[key]["number"], alarm_id, key)
            for key in orphans
            for alarm_id in unclaimed
        )
        for _, _, alarm_id, key in candidates:
            if key in claimed or alarm_id in claimed.values():
                continue
            slots[key]["alarm_id"] = alarm_id
            claimed[key] = alarm_id

        for key in [key for key in slots if key not in claimed]:
            del slots[key]

        # Alarms still without a slot are new: number them by time of day.
        for alarm_id in sorted(
            (alarm_id for alarm_id in by_id if alarm_id not in claimed.values()),
            key=lambda alarm_id: (alarm_signature(by_id[alarm_id])["time"], alarm_id),
        ):
            used = {slot["number"] for slot in slots.values()}
            number = next(number for number in range(1, len(used) + 2) if number not in used)
            key = str(alarm_id)
            while key in slots:
                key += "_"
            slots[key] = {"number": number, "alarm_id": alarm_id}
            claimed[key] = alarm_id

        for key, alarm_id in claimed.items():
            slots[key]["signature"] = alarm_signature(by_id[alarm_id])

        if not slots:
            self._things.pop(thing_name, None)
        changed = before != self._things.get(thing_name)
        return {key: by_id[alarm_id] for key, alarm_id in claimed.items()}, changed
