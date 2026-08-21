"""Custom Hatch sounds discovered outside the standard sound catalog."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any, TypedDict
from urllib.parse import unquote, urlparse


class CustomSound(TypedDict):
    """A sound payload accepted by hatch_rest_api.set_sound()."""

    id: int
    title: str
    wavUrl: str


# Add newly discovered sounds here. Keeping the complete set_sound payload in
# one place also makes sounds playable when Hatch omits them from its API list.
CUSTOM_SOUNDS: dict[str, CustomSound] = {
    "Classic Ocean": {
        "id": 10165,
        "title": "Classic Ocean",
        "wavUrl": (
            "https://downloads.ctfassets.net/hlsdh3zwyrtx/"
            "2L4XgH93PtqfypPvORIFxo/"
            "9d5eb4d5f18d182a8277a8589b27aaee/"
            "RV4_Sleep_ClassicOcean_CGMasterV5_20221020.wav"
        ),
    },
}

CUSTOM_SOUNDS_BY_ID = {sound["id"]: sound for sound in CUSTOM_SOUNDS.values()}


def sound_for_mode(sound_mode: str) -> CustomSound | str:
    """Return a complete custom payload or the original API sound title."""
    return CUSTOM_SOUNDS.get(sound_mode, sound_mode)


def sound_details(
    sound_id: int | None,
    api_sounds_by_id: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    """Describe the active sound for Home Assistant state attributes."""
    sound = CUSTOM_SOUNDS_BY_ID.get(sound_id) or api_sounds_by_id.get(sound_id)
    sound_url = None
    sound_title = None
    if sound:
        sound_url = sound.get("wavUrl") or sound.get("mp3Url")
        sound_title = sound.get("title")

    filename = None
    if sound_url:
        filename = unquote(PurePosixPath(urlparse(sound_url).path).name)

    return {
        "current_sound_id": sound_id,
        "current_sound_url": sound_url,
        "current_sound_filename": filename,
        "current_sound_title": sound_title,
    }
