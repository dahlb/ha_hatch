import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

SLOTS_MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "ha_hatch"
    / "restore_alarm_slots.py"
)
SPEC = spec_from_file_location("ha_hatch_restore_alarm_slots", SLOTS_MODULE_PATH)
slots_module = module_from_spec(SPEC)
SPEC.loader.exec_module(slots_module)
RestoreAlarmSlots = slots_module.RestoreAlarmSlots

THING = "thing-1"


def alarm(alarm_id, at="07:00:00", days=62, sound=10024, color=27, enabled=True):
    return {
        "id": alarm_id,
        "time": f"2026-01-05 {at}",
        "daysOfWeek": days,
        "sound": {"id": sound, "v": 65535},
        "color": {"id": color, "i": 65535, "duration": 1800},
        "enabled": enabled,
    }


SATURDAY = alarm(1001, at="08:30:00", days=64, color=29, enabled=False)
WEEKDAYS = alarm(1002)


class RestoreAlarmSlotsTest(unittest.TestCase):
    def test_numbers_new_alarms_by_time_of_day(self):
        slots = RestoreAlarmSlots()
        by_slot, changed = slots.reconcile(THING, [SATURDAY, WEEKDAYS])
        self.assertTrue(changed)
        self.assertEqual(by_slot, {"1002": WEEKDAYS, "1001": SATURDAY})
        self.assertEqual(slots.number(THING, "1002"), 1)
        self.assertEqual(slots.number(THING, "1001"), 2)

    def test_stable_when_nothing_changes(self):
        slots = RestoreAlarmSlots()
        slots.reconcile(THING, [SATURDAY, WEEKDAYS])
        _, changed = slots.reconcile(THING, [SATURDAY, WEEKDAYS])
        self.assertFalse(changed)

    def test_an_edit_made_here_keeps_the_slot(self):
        slots = RestoreAlarmSlots()
        slots.reconcile(THING, [SATURDAY, WEEKDAYS])
        self.assertTrue(slots.replace(THING, 1002, 5000))
        edited = alarm(5000, at="06:45:00")
        by_slot, _ = slots.reconcile(THING, [SATURDAY, edited])
        self.assertEqual(by_slot["1002"], edited)
        self.assertEqual(slots.number(THING, "1002"), 1)
        self.assertEqual(set(by_slot), {"1001", "1002"})

    def test_an_edit_made_in_the_app_is_matched_to_the_most_similar_slot(self):
        slots = RestoreAlarmSlots()
        slots.reconcile(THING, [SATURDAY, WEEKDAYS])
        # Both alarms edited elsewhere, so both ids changed. The weekday one
        # only got a new time; the Saturday one only a new sound.
        new_weekdays = alarm(5001, at="06:45:00")
        new_saturday = {**SATURDAY, "id": 5002, "sound": {"id": 10025, "v": 65535}}
        by_slot, changed = slots.reconcile(THING, [new_saturday, new_weekdays])
        self.assertTrue(changed)
        self.assertEqual(by_slot["1002"]["id"], 5001)
        self.assertEqual(by_slot["1001"]["id"], 5002)

    def test_deleted_alarm_frees_its_number_and_a_new_one_reuses_it(self):
        slots = RestoreAlarmSlots()
        slots.reconcile(THING, [SATURDAY, WEEKDAYS])
        by_slot, _ = slots.reconcile(THING, [SATURDAY])
        self.assertEqual(set(by_slot), {"1001"})
        by_slot, _ = slots.reconcile(THING, [SATURDAY, alarm(6000, at="05:00:00")])
        self.assertEqual(slots.number(THING, "6000"), 1)
        self.assertEqual(slots.number(THING, "1001"), 2)

    def test_round_trips_through_its_stored_form(self):
        slots = RestoreAlarmSlots()
        slots.reconcile(THING, [SATURDAY, WEEKDAYS])
        slots.replace(THING, 1002, 5000)
        edited = alarm(5000, at="06:45:00")
        slots.reconcile(THING, [SATURDAY, edited])
        restored = RestoreAlarmSlots(slots.as_dict())
        by_slot, changed = restored.reconcile(THING, [SATURDAY, edited])
        self.assertFalse(changed)
        self.assertEqual(by_slot["1002"]["id"], 5000)

    def test_no_alarms_leaves_no_state(self):
        slots = RestoreAlarmSlots()
        slots.reconcile(THING, [SATURDAY])
        slots.reconcile(THING, [])
        self.assertEqual(slots.as_dict(), {})
        self.assertIsNone(slots.alarm_id(THING, "1001"))


if __name__ == "__main__":
    unittest.main()
