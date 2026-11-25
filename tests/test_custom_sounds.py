"""Tests for loading user-defined Hatch sounds."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.ha_hatch import custom_sounds

CLASSIC_OCEAN_URL = (
    "https://downloads.ctfassets.net/hlsdh3zwyrtx/2L4XgH93PtqfypPvORIFxo/"
    "9d5eb4d5f18d182a8277a8589b27aaee/RV4_Sleep_ClassicOcean_CGMasterV5_20221020.wav"
)


def test_classic_ocean_has_complete_playable_payload() -> None:
    """A valid entry becomes a full set_sound payload titled by its key."""
    registry = custom_sounds.normalize_custom_sounds(
        {"ClassicOcean": {"id": 10165, "wav_url": CLASSIC_OCEAN_URL}}
    )

    assert registry == {
        "ClassicOcean": {"id": 10165, "title": "ClassicOcean", "wavUrl": CLASSIC_OCEAN_URL}
    }


@pytest.mark.parametrize("data", [None, {}])
def test_empty_document_has_no_sounds(data: Any) -> None:
    """An empty document yields no sounds."""
    assert custom_sounds.normalize_custom_sounds(data) == {}


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"id": 1, "mp3Url": "https://example.com/good.mp3"}, True),
        ({"id": 2}, False),
        ({"id": "three", "wavUrl": "https://example.com/a.wav"}, False),
        ({"id": True, "wavUrl": "https://example.com/a.wav"}, False),
        ({"id": 0, "wavUrl": "https://example.com/a.wav"}, False),
        ({"id": 4, "wavUrl": "relative.wav"}, False),
        ({"id": 5, "wavUrl": "ftp://example.com/a.wav"}, False),
        ("not a mapping", False),
    ],
)
def test_invalid_entries_are_skipped(entry: Any, expected: bool) -> None:
    """Entries without a positive id and an absolute HTTP(S) URL are skipped."""
    assert ("Sound" in custom_sounds.normalize_custom_sounds({"Sound": entry})) is expected


@pytest.mark.parametrize("name", ["", "   ", 7])
def test_invalid_names_are_skipped(name: Any) -> None:
    """Keys that are not non-blank strings are skipped."""
    registry = custom_sounds.normalize_custom_sounds(
        {name: {"id": 1, "wavUrl": "https://example.com/a.wav"}}
    )

    assert registry == {}


def test_names_are_stripped() -> None:
    """Surrounding whitespace is removed from sound-mode names."""
    registry = custom_sounds.normalize_custom_sounds(
        {"  Ocean  ": {"id": 1, "wavUrl": "https://example.com/a.wav"}}
    )

    assert registry["Ocean"]["title"] == "Ocean"


def test_duplicate_ids_are_skipped() -> None:
    """The first entry with an id wins; later duplicates are skipped."""
    registry = custom_sounds.normalize_custom_sounds(
        {
            "First": {"id": 1, "wavUrl": "https://example.com/first.wav"},
            "Second": {"id": 1, "wavUrl": "https://example.com/second.wav"},
        }
    )

    assert list(registry) == ["First"]


def test_non_mapping_document_is_rejected() -> None:
    """A document that is not a mapping raises TypeError."""
    with pytest.raises(TypeError):
        custom_sounds.normalize_custom_sounds(["not", "a", "mapping"])


def test_yaml_file_is_optional(tmp_path: Path) -> None:
    """A missing file yields no sounds."""
    assert custom_sounds.load_custom_sounds_file(tmp_path / "missing.yaml") == {}


def test_yaml_file_loads_camel_case_and_snake_case_urls(tmp_path: Path) -> None:
    """Both camel-case and snake-case URL keys load."""
    path = tmp_path / "sounds.yaml"
    path.write_text(
        "Ocean One:\n  id: 10165\n  wavUrl: https://example.com/ocean.wav\n"
        "Rain Two:\n  id: 10166\n  mp3_url: https://example.com/rain.mp3\n",
        encoding="utf-8",
    )

    registry = custom_sounds.load_custom_sounds_file(path)

    assert registry["Ocean One"]["wavUrl"] == "https://example.com/ocean.wav"
    assert registry["Rain Two"]["mp3Url"] == "https://example.com/rain.mp3"


@pytest.mark.parametrize("content", ["- not\n- a\n- mapping\n", "key: [unclosed\n"])
def test_bad_yaml_file_is_ignored(tmp_path: Path, content: str) -> None:
    """A file that is not a mapping or not valid YAML yields no sounds."""
    path = tmp_path / "sounds.yaml"
    path.write_text(content, encoding="utf-8")

    assert custom_sounds.load_custom_sounds_file(path) == {}


async def test_async_load_reads_from_the_config_directory(tmp_path: Path) -> None:
    """The async loader reads hatch_custom_sounds.yaml from the config directory."""
    (tmp_path / custom_sounds.CUSTOM_SOUNDS_FILENAME).write_text(
        "Ocean:\n  id: 1\n  wavUrl: https://example.com/ocean.wav\n", encoding="utf-8"
    )
    hass = MagicMock()
    hass.config.path.side_effect = lambda name: str(tmp_path / name)

    async def run_in_executor(func: Any, *args: Any) -> Any:
        """Run the executor job inline.

        Args:
            func: Function to run.
            *args: Arguments for the function.

        Returns:
            The function's result.
        """
        return func(*args)

    hass.async_add_executor_job = run_in_executor

    registry = await custom_sounds.async_load_custom_sounds(hass)

    assert list(registry) == ["Ocean"]


def test_sound_details_prefers_custom_registry() -> None:
    """A custom sound's metadata wins over the device catalog for the same id."""
    details = custom_sounds.sound_details(
        10165,
        {10165: {"title": "Stormy Sea", "wavUrl": "https://example.com/api-name.wav"}},
        {10165: {"id": 10165, "title": "ClassicOcean", "wavUrl": CLASSIC_OCEAN_URL}},
    )

    assert details == {
        "current_sound_id": 10165,
        "current_sound_url": CLASSIC_OCEAN_URL,
        "current_sound_filename": "RV4_Sleep_ClassicOcean_CGMasterV5_20221020.wav",
        "current_sound_title": "ClassicOcean",
    }


def test_sound_details_uses_api_metadata_for_other_sounds() -> None:
    """Sounds from the device catalog are described, with the file name unquoted."""
    details = custom_sounds.sound_details(
        42, {42: {"title": "Rain", "mp3Url": "https://example.com/sounds/Rain%20Loop.mp3"}}, {}
    )

    assert details["current_sound_title"] == "Rain"
    assert details["current_sound_filename"] == "Rain Loop.mp3"


@pytest.mark.parametrize("sound_id", [None, 99])
def test_sound_details_for_unknown_sound(sound_id: int | None) -> None:
    """An unknown or absent sound is described with None values."""
    assert custom_sounds.sound_details(sound_id, {}, {}) == {
        "current_sound_id": sound_id,
        "current_sound_url": None,
        "current_sound_filename": None,
        "current_sound_title": None,
    }
