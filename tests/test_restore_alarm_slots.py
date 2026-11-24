"""Tests for the original Restore's alarm slots and alarm entity unique ids."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.ha_hatch.restore_alarm_slots import (
    RestoreAlarmSlots,
    alarm_section,
    restore_alarm_reference_from_unique_id,
    restore_alarm_unique_id,
)

THING = "thing-1"


def _alarm(
    alarm_id: int,
    at: str = "07:00:00",
    days: int = 62,
    sound: int = 10024,
    color: int = 27,
    enabled: bool = True,
) -> dict[str, Any]:
    """Build an alarm as Hatch's alarm API returns it.

    Args:
        alarm_id: The alarm's id.
        at: Its time of day.
        days: Its ``daysOfWeek`` bitmask.
        sound: Its sound id.
        color: Its sunrise color id.
        enabled: Whether it goes off.

    Returns:
        The alarm.
    """
    return {
        "id": alarm_id,
        "time": f"2026-01-05 {at}",
        "daysOfWeek": days,
        "sound": {"id": sound, "v": 65535},
        "color": {"id": color, "i": 65535, "duration": 1800},
        "enabled": enabled,
    }


SATURDAY = _alarm(1001, at="08:30:00", days=64, color=29, enabled=False)
WEEKDAYS = _alarm(1002)


@pytest.fixture
def slots() -> RestoreAlarmSlots:
    """Slots that have seen the Saturday and weekday alarms.

    Returns:
        The slots.
    """
    slots = RestoreAlarmSlots()
    slots.reconcile(THING, [SATURDAY, WEEKDAYS])
    return slots


def test_numbers_new_alarms_by_time_of_day() -> None:
    """New alarms are numbered by when in the day they go off."""
    slots = RestoreAlarmSlots()

    by_slot, changed = slots.reconcile(THING, [SATURDAY, WEEKDAYS])

    assert changed
    assert by_slot == {"1002": WEEKDAYS, "1001": SATURDAY}
    assert slots.number(THING, "1002") == 1
    assert slots.number(THING, "1001") == 2
    assert slots.alarm_id(THING, "1001") == 1001


def test_stable_when_nothing_changes(slots: RestoreAlarmSlots) -> None:
    """The same alarms again change nothing."""
    _, changed = slots.reconcile(THING, [SATURDAY, WEEKDAYS])
    assert not changed


def test_an_edit_made_here_keeps_the_slot(slots: RestoreAlarmSlots) -> None:
    """An edit reported with its old and new id keeps its slot and number."""
    assert slots.replace(THING, 1002, 5000)
    edited = _alarm(5000, at="06:45:00")

    by_slot, _ = slots.reconcile(THING, [SATURDAY, edited])

    assert by_slot["1002"] == edited
    assert slots.number(THING, "1002") == 1
    assert set(by_slot) == {"1001", "1002"}


def test_replacing_an_unknown_alarm_moves_nothing(slots: RestoreAlarmSlots) -> None:
    """Replacing an id no slot holds reports that nothing moved."""
    assert not slots.replace(THING, 9999, 5000)


def test_an_edit_made_in_the_app_is_matched_to_the_most_similar_slot(
    slots: RestoreAlarmSlots,
) -> None:
    """Alarms replaced elsewhere go back to the slot they most resemble."""
    # Both alarms edited elsewhere, so both ids changed. The weekday one only
    # got a new time; the Saturday one only a new sound.
    new_weekdays = _alarm(5001, at="06:45:00")
    new_saturday = {**SATURDAY, "id": 5002, "sound": {"id": 10025, "v": 65535}}

    by_slot, changed = slots.reconcile(THING, [new_saturday, new_weekdays])

    assert changed
    assert by_slot["1002"]["id"] == 5001
    assert by_slot["1001"]["id"] == 5002


def test_deleted_alarm_frees_its_number_and_a_new_one_reuses_it(
    slots: RestoreAlarmSlots,
) -> None:
    """A deleted alarm's slot goes, and its number is reused."""
    by_slot, _ = slots.reconcile(THING, [SATURDAY])
    assert set(by_slot) == {"1001"}

    slots.reconcile(THING, [SATURDAY, _alarm(6000, at="05:00:00")])

    assert slots.number(THING, "6000") == 1
    assert slots.number(THING, "1001") == 2


def test_round_trips_through_its_stored_form(slots: RestoreAlarmSlots) -> None:
    """Saved and loaded slots carry on where they left off."""
    slots.replace(THING, 1002, 5000)
    edited = _alarm(5000, at="06:45:00")
    slots.reconcile(THING, [SATURDAY, edited])

    restored = RestoreAlarmSlots(slots.as_dict())
    by_slot, changed = restored.reconcile(THING, [SATURDAY, edited])

    assert not changed
    assert by_slot["1002"]["id"] == 5000


def test_no_alarms_leaves_no_state() -> None:
    """A device without alarms keeps no state."""
    slots = RestoreAlarmSlots()
    slots.reconcile(THING, [SATURDAY])

    slots.reconcile(THING, [])

    assert slots.as_dict() == {}
    assert slots.alarm_id(THING, "1001") is None
    assert slots.number(THING, "1001") is None


def test_alarms_without_a_usable_id_are_ignored() -> None:
    """An alarm with no id, or one that is not a number, gets no slot."""
    by_slot, _ = RestoreAlarmSlots().reconcile(THING, [{"time": "x"}, {"id": "abc"}, WEEKDAYS])
    assert list(by_slot) == ["1002"]


def test_alarm_section() -> None:
    """A missing or malformed section reads as empty."""
    assert alarm_section(WEEKDAYS, "sound") == {"id": 10024, "v": 65535}
    assert alarm_section({"sound": "loud"}, "sound") == {}
    assert alarm_section({}, "color") == {}


def test_unique_ids_round_trip() -> None:
    """A slot's unique id reads back as its device and slot."""
    unique_id = restore_alarm_unique_id(THING, "1002", "_time")

    assert unique_id == f"{THING}_restore_alarm_1002_time"
    assert restore_alarm_reference_from_unique_id(unique_id, {"_switch", "_time"}) == (
        THING,
        "1002",
    )


@pytest.mark.parametrize(
    "unique_id",
    [None, f"{THING}_light", f"{THING}_restore_alarm_1002_other", "_restore_alarm_1002_time"],
)
def test_other_unique_ids_are_not_alarms(unique_id: str | None) -> None:
    """Unique ids of other entities, or without a device, are not slots."""
    assert restore_alarm_reference_from_unique_id(unique_id, {"_switch", "_time"}) is None
