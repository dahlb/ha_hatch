from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def favorite_scene_name(
    favorite_name: str,
    preset_number: int,
    show_preset_number: bool,
) -> str:
    if not show_preset_number:
        return favorite_name

    return f"Preset {preset_number} - {favorite_name}"


def favorite_scene_attributes(
    favorite: Mapping[str, Any],
    preset_number: int,
) -> dict[str, Any]:
    return {
        "preset_number": preset_number,
        "hatch_favorite_id": favorite.get("id"),
        "hatch_display_order": favorite.get("displayOrder"),
    }
