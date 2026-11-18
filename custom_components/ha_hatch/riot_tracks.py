from __future__ import annotations

from typing import Any

from hatch_rest_api import TimeForBedTrack, TimeToRiseTrack

_PROGRAM_TRACK_PREFIXES = (
    (TimeToRiseTrack, "TimeToRise"),
    (TimeForBedTrack, "TimeForBed"),
)


def _build_program_sounds() -> dict[str, dict[str, Any]]:
    sounds: dict[str, dict[str, Any]] = {}
    for track_class, prefix in _PROGRAM_TRACK_PREFIXES:
        url_map = track_class.track_url_map()
        for track in track_class:
            if track is track_class.NONE:
                continue
            name = f"{prefix}.{track.name}"
            sounds[name] = {
                "id": track.value,
                "title": name,
                "mp3Url": url_map[track.value],
            }
    return sounds


PROGRAM_SOUNDS = _build_program_sounds()
_PROGRAM_SOUND_NAMES_BY_ID = {
    sound["id"]: name for name, sound in PROGRAM_SOUNDS.items()
}


def program_sound_name(sound_id: int | None) -> str | None:
    return _PROGRAM_SOUND_NAMES_BY_ID.get(sound_id)
