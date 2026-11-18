"""Tests for the favorite scene helpers."""

from collections.abc import Mapping
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast
import unittest

FAVORITES_MODULE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "ha_hatch" / "favorites.py"
)


class FavoritesModule(Protocol):
    """Typed stand-in for the favorites module."""

    def favorite_scene_name(
        self,
        favorite_name: str,
        preset_number: int,
        show_preset_number: bool,
    ) -> str:
        """Return the display name for a favorite scene."""
        ...

    def favorite_scene_attributes(
        self,
        favorite: Mapping[str, Any],
        preset_number: int,
    ) -> dict[str, Any]:
        """Return state attributes for a favorite scene."""
        ...


def load_favorites_module() -> FavoritesModule:
    """Load the favorites module under test."""
    spec = spec_from_file_location("ha_hatch_favorites", FAVORITES_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load favorites module from {FAVORITES_MODULE_PATH}")

    module: ModuleType = module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("FavoritesModule", module)


class FavoriteHelperTest(unittest.TestCase):
    """Tests for the favorite scene helpers."""

    def test_favorite_scene_name_keeps_existing_name_by_default(self) -> None:
        """Test favorite scene name keeps existing name by default."""
        favorites = load_favorites_module()

        assert favorites.favorite_scene_name("Ocean", 1, False) == "Ocean"

    def test_favorite_scene_name_can_include_preset_number(self) -> None:
        """Test favorite scene name can include preset number."""
        favorites = load_favorites_module()

        assert favorites.favorite_scene_name("Forest Lake", 2, True) == "Preset 2 - Forest Lake"

    def test_favorite_scene_attributes_include_preset_mapping(self) -> None:
        """Test favorite scene attributes include preset mapping."""
        favorites = load_favorites_module()

        assert favorites.favorite_scene_attributes({"id": 223167108, "displayOrder": 1}, 2) == {
            "preset_number": 2,
            "hatch_favorite_id": 223167108,
            "hatch_display_order": 1,
        }


if __name__ == "__main__":
    unittest.main()
