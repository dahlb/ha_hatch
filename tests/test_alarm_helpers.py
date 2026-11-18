"""Tests for the alarm helpers."""

from datetime import time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

import pytest

ALARM_MODULE_PATH = Path(__file__).parents[1] / "custom_components" / "ha_hatch" / "alarm.py"
SPEC = spec_from_file_location("ha_hatch_alarm_helpers", ALARM_MODULE_PATH)
alarm_helpers = module_from_spec(SPEC)
SPEC.loader.exec_module(alarm_helpers)


class AlarmHelperTest(unittest.TestCase):
    """Tests for the alarm helpers."""

    def test_alarm_base_names_handles_default_and_named_alarms(self) -> None:
        """Test alarm base names handles default and named alarms."""
        alarms = [
            {"id": 1, "name": "Alarm_Default_Name"},
            {"id": 2, "name": ""},
            {"id": 3, "name": "Weekend_Wake"},
        ]

        assert list(alarm_helpers.alarm_base_names(alarms)) == [
            (1, "Default Alarm"),
            (2, "Alarm - 2"),
            (3, "Weekend Wake Alarm"),
        ]

    def test_alarm_unique_id_uses_device_alarm_and_suffix(self) -> None:
        """Test alarm unique id uses device alarm and suffix."""
        assert (
            alarm_helpers.alarm_unique_id("thing-name", 42, "_wake_time")
            == "thing-name_alarm_42_wake_time"
        )

    def test_alarm_reference_from_unique_id_accepts_alarm_entity_suffixes(self) -> None:
        """Test alarm reference from unique id accepts alarm entity suffixes."""
        assert alarm_helpers.alarm_reference_from_unique_id(
            "thing-name_alarm_42_wake_time", {"_switch", "_wake_time"}
        ) == ("thing-name", "42")
        assert alarm_helpers.alarm_reference_from_unique_id(
            "thing-name_alarm_42_switch", {"_switch", "_wake_time"}
        ) == ("thing-name", "42")
        assert (
            alarm_helpers.alarm_reference_from_unique_id(
                "thing-name_power_switch", {"_switch", "_wake_time"}
            )
            is None
        )

    def test_alarm_repeat_attributes_describe_days_of_week(self) -> None:
        """Test alarm repeat attributes describe days of week."""
        assert alarm_helpers.alarm_repeat_attributes({"daysOfWeek": 62}) == {
            "repeat": "Weekdays",
            "weekdays": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "days_of_week": 62,
        }
        assert alarm_helpers.alarm_repeat_attributes({"daysOfWeek": 65})["repeat"] == "Weekends"
        assert alarm_helpers.alarm_repeat_attributes({"daysOfWeek": 127})["repeat"] == "Every day"
        assert alarm_helpers.alarm_repeat_attributes({"daysOfWeek": 42}) == {
            "repeat": "Mon, Wed, Fri",
            "weekdays": ["monday", "wednesday", "friday"],
            "days_of_week": 42,
        }
        assert alarm_helpers.alarm_repeat_attributes({"daysOfWeek": 0}) == {
            "repeat": "Once",
            "weekdays": [],
            "days_of_week": 0,
        }
        assert alarm_helpers.alarm_repeat_attributes({"daysOfWeek": 127})["weekdays"] == [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        assert alarm_helpers.alarm_repeat_attributes({"daysOfWeek": "bad"}) == {
            "repeat": "Unknown",
            "weekdays": [],
            "days_of_week": "bad",
        }

    def test_normalize_alarm_weekdays_accepts_ui_values(self) -> None:
        """Test normalize alarm weekdays accepts ui values."""
        assert alarm_helpers.normalize_alarm_weekdays([" Monday ", "FRIDAY"]) == [
            "monday",
            "friday",
        ]
        assert alarm_helpers.normalize_alarm_weekdays([]) == []
        with pytest.raises(ValueError, match="Unsupported alarm weekday"):
            alarm_helpers.normalize_alarm_weekdays(["funday"])
        with pytest.raises(ValueError, match="must be a list"):
            alarm_helpers.normalize_alarm_weekdays(62)

    def test_alarm_wake_time_reads_end_time_and_derives_missing_end_time(self) -> None:
        """Test alarm wake time reads end time and derives missing end time."""
        assert alarm_helpers.alarm_wake_time(
            {"startTime": "2026-05-08T07:30:00", "endTime": "2026-05-08T08:00:00"}
        ) == time(8, 0)
        assert alarm_helpers.alarm_wake_time(
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
        ) == time(11, 30)
        assert (
            alarm_helpers.alarm_wake_time({"startTime": "2026-05-08T10:45:00", "endTime": None})
            is None
        )
        assert (
            alarm_helpers.alarm_wake_time({"startTime": None, "endTime": "2026-05-08T08:00:00"})
            is None
        )
        assert (
            alarm_helpers.alarm_wake_time(
                {"startTime": "2026-05-08T07:30:00", "endTime": "not-a-date"}
            )
            is None
        )


if __name__ == "__main__":
    unittest.main()
