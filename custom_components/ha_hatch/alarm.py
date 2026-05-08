from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

DEFAULT_ALARM_NAME = "alarm default name"
ALARM_UNIQUE_ID_MARKER = "_alarm_"
ALARM_WEEKDAY_BITS: dict[str, int] = {
    "monday": 2,
    "tuesday": 4,
    "wednesday": 8,
    "thursday": 16,
    "friday": 32,
    "saturday": 64,
    "sunday": 1,
}
ALARM_WEEKDAY_LABELS: dict[str, str] = {
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
    "sunday": "Sun",
}
ALARM_WEEKDAYS_MASK = sum(ALARM_WEEKDAY_BITS.values())
ALARM_WEEKDAYS_ONLY_MASK = (
    ALARM_WEEKDAY_BITS["monday"]
    | ALARM_WEEKDAY_BITS["tuesday"]
    | ALARM_WEEKDAY_BITS["wednesday"]
    | ALARM_WEEKDAY_BITS["thursday"]
    | ALARM_WEEKDAY_BITS["friday"]
)
ALARM_WEEKENDS_MASK = ALARM_WEEKDAY_BITS["sunday"] | ALARM_WEEKDAY_BITS["saturday"]


def alarm_base_names(alarms: list[dict[str, Any]]):
    default_alarm_count = 0
    for alarm in alarms:
        alarm_id = alarm.get("id")
        if alarm_id is None:
            continue

        alarm_name = _clean_alarm_name(alarm.get("name"))
        if _is_default_alarm_name(alarm_name):
            default_alarm_count += 1
            if default_alarm_count == 1:
                yield alarm_id, "Default Alarm"
                continue
            alarm_name = str(default_alarm_count)
            yield alarm_id, f"Alarm - {alarm_name}"
            continue

        yield alarm_id, f"{alarm_name} Alarm"


def alarm_by_id(rest_device, alarm_id: int | str) -> dict[str, Any] | None:
    get_alarm_by_id = getattr(rest_device, "alarm_by_id", None)
    if callable(get_alarm_by_id):
        return get_alarm_by_id(alarm_id)

    alarm_id_string = str(alarm_id)
    return next(
        (
            alarm
            for alarm in getattr(rest_device, "alarms", [])
            if str(alarm.get("id")) == alarm_id_string
        ),
        None,
    )


def alarm_wake_time(alarm: dict[str, Any] | None) -> time | None:
    if alarm is None:
        return None
    parsed_start_time = _parse_alarm_datetime(alarm.get("startTime"))
    parsed_end_time = _parse_alarm_datetime(alarm.get("endTime"))
    if parsed_start_time is None:
        return None
    if parsed_end_time is not None:
        return parsed_end_time.time()
    if alarm.get("endTime") is None:
        sunrise_duration = _alarm_sunrise_duration_seconds(alarm)
        if sunrise_duration is not None:
            return (parsed_start_time + timedelta(seconds=sunrise_duration)).time()
    return None


def alarm_has_valid_wake_times(alarm: dict[str, Any]) -> bool:
    if _parse_alarm_datetime(alarm.get("startTime")) is None:
        return False
    if alarm.get("endTime") is None:
        return _alarm_sunrise_duration_seconds(alarm) is not None
    return _parse_alarm_datetime(alarm.get("endTime")) is not None


def alarm_unique_id(thing_name: str, alarm_id: int | str, suffix: str) -> str:
    return f"{alarm_unique_id_prefix(thing_name)}{alarm_id}{suffix}"


def alarm_unique_id_prefix(thing_name: str) -> str:
    return f"{thing_name}{ALARM_UNIQUE_ID_MARKER}"


def alarm_reference_from_unique_id(
    unique_id: str | None,
    suffixes: set[str],
) -> tuple[str, str] | None:
    if not unique_id:
        return None

    for suffix in sorted(suffixes, key=len, reverse=True):
        if not unique_id.endswith(suffix):
            continue
        unique_id_without_suffix = unique_id[: -len(suffix)]
        thing_name, marker, alarm_id = unique_id_without_suffix.rpartition(
            ALARM_UNIQUE_ID_MARKER
        )
        if marker and thing_name and alarm_id:
            return thing_name, alarm_id

    return None


def alarm_repeat_attributes(alarm: dict[str, Any] | None) -> dict[str, Any]:
    if alarm is None:
        return {}

    days_of_week = alarm.get("daysOfWeek")
    return {
        "repeat": alarm_repeat_label(days_of_week),
        "weekdays": alarm_weekdays(days_of_week),
        "days_of_week": days_of_week,
    }


def alarm_weekdays(days_of_week: Any) -> list[str]:
    normalized_days_of_week = _normalize_days_of_week(days_of_week)
    if normalized_days_of_week is None:
        return []
    return [
        weekday
        for weekday, bit in ALARM_WEEKDAY_BITS.items()
        if normalized_days_of_week & bit
    ]


def alarm_repeat_label(days_of_week: Any) -> str:
    normalized_days_of_week = _normalize_days_of_week(days_of_week)
    if normalized_days_of_week is None:
        return "Unknown"
    if normalized_days_of_week == 0:
        return "Once"
    if normalized_days_of_week == ALARM_WEEKDAYS_ONLY_MASK:
        return "Weekdays"
    if normalized_days_of_week == ALARM_WEEKENDS_MASK:
        return "Weekends"
    if normalized_days_of_week == ALARM_WEEKDAYS_MASK:
        return "Every day"
    return ", ".join(
        ALARM_WEEKDAY_LABELS[weekday]
        for weekday in alarm_weekdays(normalized_days_of_week)
    )


def normalize_alarm_weekdays(weekdays: Any) -> list[str]:
    if weekdays is None:
        return []
    if isinstance(weekdays, str):
        weekdays = [weekdays]

    normalized_weekdays = []
    try:
        weekday_values = iter(weekdays)
    except TypeError as error:
        raise ValueError("Alarm weekdays must be a list of weekday names") from error

    for weekday in weekday_values:
        normalized_weekday = str(weekday).strip().lower()
        if normalized_weekday not in ALARM_WEEKDAY_BITS:
            raise ValueError(f"Unsupported alarm weekday: {weekday}")
        normalized_weekdays.append(normalized_weekday)

    return normalized_weekdays


def remove_stale_alarm_entities(
    hass,
    config_entry,
    domain: str,
    current_alarm_unique_ids: set[str],
    authoritative_alarm_unique_id_prefixes: set[str],
    unique_id_suffix: str,
) -> None:
    if not authoritative_alarm_unique_id_prefixes:
        return

    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)
    for entry in er.async_entries_for_config_entry(
        entity_registry,
        config_entry.entry_id,
    ):
        if entry.domain != domain:
            continue
        if entry.unique_id in current_alarm_unique_ids:
            continue
        if _is_alarm_unique_id_for_authoritative_device(
            entry.unique_id,
            authoritative_alarm_unique_id_prefixes,
            unique_id_suffix,
        ):
            entity_registry.async_remove(entry.entity_id)


def update_alarm_entity_names(
    hass,
    config_entry,
    domain: str,
    current_alarm_names: dict[str, str],
) -> None:
    if not current_alarm_names:
        return

    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)
    for entry in er.async_entries_for_config_entry(
        entity_registry,
        config_entry.entry_id,
    ):
        alarm_name = current_alarm_names.get(entry.unique_id)
        if entry.domain != domain or alarm_name is None:
            continue
        if entry.original_name != alarm_name:
            entity_registry.async_update_entity(
                entry.entity_id,
                original_name=alarm_name,
            )


def _clean_alarm_name(alarm_name: Any) -> str:
    if alarm_name is None:
        return ""
    return " ".join(str(alarm_name).replace("_", " ").split())


def _is_default_alarm_name(alarm_name: str) -> bool:
    return alarm_name.lower() in {"", "default", DEFAULT_ALARM_NAME}


def _normalize_days_of_week(days_of_week: Any) -> int | None:
    if days_of_week is None:
        return None
    if isinstance(days_of_week, bool) or not isinstance(days_of_week, int):
        return None
    if days_of_week < 0 or days_of_week > ALARM_WEEKDAYS_MASK:
        return None
    return days_of_week


def _parse_alarm_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed


def _alarm_sunrise_duration_seconds(alarm: dict[str, Any]) -> int | None:
    steps = alarm.get("steps") or []
    sunrise_step_duration = next(
        (
            duration
            for step in steps
            if isinstance(step, dict)
            and str(step.get("name", "")).lower() == "sunrise"
            and (duration := _step_color_duration_seconds(step)) is not None
        ),
        None,
    )
    if sunrise_step_duration is not None:
        return sunrise_step_duration

    return next(
        (
            duration
            for step in steps
            if isinstance(step, dict)
            and (duration := _step_color_duration_seconds(step)) is not None
        ),
        None,
    )


def _step_color_duration_seconds(step: dict[str, Any]) -> int | None:
    if step.get("enabled") is False:
        return None

    color = step.get("color")
    if not isinstance(color, dict) or color.get("ignore") is True:
        return None

    duration = color.get("duration")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
        return None

    return duration


def _is_alarm_unique_id_for_authoritative_device(
    unique_id: str,
    authoritative_alarm_unique_id_prefixes: set[str],
    unique_id_suffix: str,
) -> bool:
    return unique_id.endswith(unique_id_suffix) and any(
        unique_id.startswith(prefix)
        for prefix in authoritative_alarm_unique_id_prefixes
    )
