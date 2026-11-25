"""Load user-defined Hatch sounds from the Home Assistant config directory."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, TypedDict
from urllib.parse import unquote, urlparse

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.yaml import load_yaml

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CUSTOM_SOUNDS_FILENAME = "hatch_custom_sounds.yaml"


class CustomSound(TypedDict, total=False):
    """A sound payload accepted by hatch_rest_api ``set_sound()``."""

    id: int
    title: str
    wavUrl: str
    mp3Url: str


def _normalize_sound(name: str, value: Any) -> CustomSound:
    """Validate and normalize one custom sound definition.

    Args:
        name: Sound-mode name, used as the payload title.
        value: Raw YAML value for the sound.

    Returns:
        The normalized sound payload.

    Raises:
        TypeError: If the definition is not a mapping or has no URL string.
        ValueError: If the id or URL is invalid.
    """
    if not isinstance(value, Mapping):
        raise TypeError("definition must be a mapping")

    sound_id = value.get("id")
    if isinstance(sound_id, bool) or not isinstance(sound_id, int) or sound_id <= 0:
        raise ValueError("id must be a positive integer")

    wav_url = value.get("wavUrl") or value.get("wav_url")
    mp3_url = value.get("mp3Url") or value.get("mp3_url")
    sound_url = wav_url or mp3_url
    if not isinstance(sound_url, str):
        raise TypeError("wavUrl/wav_url or mp3Url/mp3_url is required")

    parsed_url = urlparse(sound_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("sound URL must be an absolute HTTP or HTTPS URL")

    sound: CustomSound = {"id": sound_id, "title": name}
    if wav_url:
        sound["wavUrl"] = sound_url
    else:
        sound["mp3Url"] = sound_url
    return sound


def normalize_custom_sounds(data: Any) -> dict[str, CustomSound]:
    """Normalize a YAML document, skipping invalid sound entries.

    Args:
        data: Parsed YAML document.

    Returns:
        Valid sounds keyed by sound-mode name.

    Raises:
        TypeError: If the document is not a mapping.
    """
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise TypeError("top-level YAML value must be a mapping")

    custom_sounds: dict[str, CustomSound] = {}
    sound_ids: set[int] = set()
    for name, value in data.items():
        if not isinstance(name, str) or not name.strip():
            _LOGGER.error("Ignoring custom Hatch sound with an invalid name")
            continue
        try:
            sound = _normalize_sound(name.strip(), value)
        except (TypeError, ValueError) as err:
            _LOGGER.error("Ignoring custom Hatch sound %r: %s", name, err)
            continue
        if sound["id"] in sound_ids:
            _LOGGER.error(
                "Ignoring custom Hatch sound %r: duplicate id %s",
                name,
                sound["id"],
            )
            continue
        custom_sounds[name.strip()] = sound
        sound_ids.add(sound["id"])
    return custom_sounds


def load_custom_sounds_file(path: str | Path) -> dict[str, CustomSound]:
    """Load custom sounds from a YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        Valid sounds keyed by sound-mode name; empty if the file is absent or unreadable.
    """
    try:
        return normalize_custom_sounds(load_yaml(path))
    except FileNotFoundError:
        return {}
    except (HomeAssistantError, OSError, TypeError, ValueError) as err:
        _LOGGER.error("Unable to load custom Hatch sounds from %s: %s", path, err)
        return {}


async def async_load_custom_sounds(hass: HomeAssistant) -> dict[str, CustomSound]:
    """Load custom sounds without blocking Home Assistant's event loop.

    Args:
        hass: Home Assistant instance, used to resolve the config directory.

    Returns:
        Valid sounds keyed by sound-mode name.
    """
    path = hass.config.path(CUSTOM_SOUNDS_FILENAME)
    custom_sounds = await hass.async_add_executor_job(load_custom_sounds_file, path)
    _LOGGER.debug("Loaded %s custom Hatch sounds from %s", len(custom_sounds), path)
    return custom_sounds


def sound_details(
    sound_id: int | None,
    api_sounds_by_id: Mapping[int, Mapping[str, Any]],
    custom_sounds_by_id: Mapping[int, CustomSound],
) -> dict[str, Any]:
    """Describe the active sound for Home Assistant state attributes.

    Args:
        sound_id: Id of the sound the device is playing.
        api_sounds_by_id: The device's own sound catalog keyed by id.
        custom_sounds_by_id: User-defined sounds keyed by id; these win over the catalog.

    Returns:
        The sound id, URL, file name and title (each None when unknown).
    """
    sound: Mapping[str, Any] | None = None
    if sound_id is not None:
        sound = custom_sounds_by_id.get(sound_id) or api_sounds_by_id.get(sound_id)
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
