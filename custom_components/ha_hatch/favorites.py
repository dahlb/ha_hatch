"""Favorite scene helpers for Hatch devices."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def favorite_scene_name(
    favorite_name: str,
    preset_number: int,
    show_preset_number: bool,
) -> str:
    """Return the display name for a favorite scene."""
    if not show_preset_number:
        return favorite_name

    return f"Preset {preset_number} - {favorite_name}"


def favorite_scene_attributes(
    favorite: Mapping[str, Any],
    preset_number: int,
) -> dict[str, Any]:
    """Return state attributes for a favorite scene."""
    return {
        "preset_number": preset_number,
        "hatch_favorite_id": favorite.get("id"),
        "hatch_display_order": favorite.get("displayOrder"),
    }
