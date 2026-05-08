from datetime import time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

ALARM_MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "ha_hatch"
    / "alarm.py"
)
SPEC = spec_from_file_location("ha_hatch_alarm_helpers", ALARM_MODULE_PATH)
alarm_helpers = module_from_spec(SPEC)
SPEC.loader.exec_module(alarm_helpers)


class AlarmHelperTest(unittest.TestCase):
    def test_alarm_base_names_handles_default_and_named_alarms(self):
        alarms = [
            {"id": 1, "name": "Alarm_Default_Name"},
            {"id": 2, "name": ""},
            {"id": 3, "name": "Weekend_Wake"},
        ]

        self.assertEqual(
            list(alarm_helpers.alarm_base_names(alarms)),
            [
                (1, "Alarm - Default"),
                (2, "Alarm - 2"),
                (3, "Alarm - Weekend Wake"),
            ],
        )

    def test_alarm_unique_id_uses_device_alarm_and_suffix(self):
        self.assertEqual(
            alarm_helpers.alarm_unique_id("thing-name", 42, "_wake_time"),
            "thing-name_alarm_42_wake_time",
        )

    def test_alarm_wake_time_reads_end_time_and_derives_missing_end_time(self):
        self.assertEqual(
            alarm_helpers.alarm_wake_time(
                {
                    "startTime": "2026-05-08T07:30:00",
                    "endTime": "2026-05-08T08:00:00",
                }
            ),
            time(8, 0),
        )
        self.assertEqual(
            alarm_helpers.alarm_wake_time(
                {
                    "startTime": "2026-05-08T10:45:00",
                    "endTime": None,
                    "steps": [
                        {
                            "name": "Sunrise",
                            "enabled": True,
                            "color": {"duration": 2700, "ignore": False},
                        }
                    ],
                }
            ),
            time(11, 30),
        )
        self.assertIsNone(
            alarm_helpers.alarm_wake_time(
                {
                    "startTime": "2026-05-08T10:45:00",
                    "endTime": None,
                }
            )
        )
        self.assertIsNone(
            alarm_helpers.alarm_wake_time(
                {
                    "startTime": None,
                    "endTime": "2026-05-08T08:00:00",
                }
            )
        )
        self.assertIsNone(
            alarm_helpers.alarm_wake_time(
                {
                    "startTime": "2026-05-08T07:30:00",
                    "endTime": "not-a-date",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
