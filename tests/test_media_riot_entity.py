"""Tests for the Hatch riot media player entity."""

from unittest.mock import MagicMock

from hatch_rest_api import (
    RestBaby,
    RestBabyAudioTrack,
    RestIot,
    RestoreIot,
    RestoreV4,
    RestoreV5,
    RIoTAudioTrack,
)
from hatch_rest_api.const import NO_SOUND_ID
import pytest

from custom_components.ha_hatch.media_riot_entity import MediaRiotEntity

RESTORE_CATALOG = [
    {"id": 20001, "title": "432 Hz Ambience", "wavUrl": "https://example.invalid/432.wav"},
    {"id": 20002, "title": "Meditative Flute", "wavUrl": "https://example.invalid/flute.wav"},
]
RIOT_TRACK_NAMES = {track.name for track in RIoTAudioTrack if track is not RIoTAudioTrack.NONE}


def _media_entity(
    device_class: type, sounds: list[dict[str, object]] | None = None
) -> tuple[MediaRiotEntity, MagicMock]:
    """Build a media entity backed by a mocked coordinator and device.

    Args:
        device_class: hatch_rest_api device class the mocked device is specced on.
        sounds: Sound catalog the device was created with.

    Returns:
        The media entity under test and its mocked device.
    """
    rest_device = MagicMock(spec=device_class)
    rest_device.device_name = "Hatch"
    rest_device.mac = "AA:BB:CC:DD:EE:FF"
    rest_device.firmware_version = "1.0"
    rest_device.sound_id = NO_SOUND_ID
    rest_device.is_playing = False
    if hasattr(device_class, "audio_track"):
        rest_device.audio_track = None
    sounds = sounds or []
    rest_device.sounds_by_name = {sound["title"]: sound for sound in sounds}
    rest_device.sounds_by_id = {sound["id"]: sound for sound in sounds}
    coordinator = MagicMock()
    coordinator.rest_device_by_thing_name.return_value = rest_device
    return MediaRiotEntity(coordinator=coordinator, thing_name="thing"), rest_device


@pytest.mark.parametrize("device_class", [RestoreV4, RestoreV5])
def test_restore_offers_only_its_catalog(device_class: type) -> None:
    """A Restore lists the sounds in its own catalog and none of the Rest tracks."""
    entity, _ = _media_entity(device_class, RESTORE_CATALOG)

    assert entity.sound_mode_list == ["432 Hz Ambience", "Meditative Flute"]


@pytest.mark.parametrize("device_class", [RestoreV4, RestoreV5])
@pytest.mark.parametrize("sound_mode", ["Meditative Flute", "Rain"])
def test_restore_select_sound_mode_uses_set_sound(device_class: type, sound_mode: str) -> None:
    """A Restore plays any sound mode by title, including a Rest track name.

    RestoreV4/V5 have no set_audio_track; a Rest track name used to raise
    AttributeError ('RestoreV4' object has no attribute 'set_audio_track').
    """
    entity, rest_device = _media_entity(device_class, RESTORE_CATALOG)

    entity.select_sound_mode(sound_mode)

    rest_device.set_sound.assert_called_once_with(sound_mode)


def test_restore_media_play_starts_first_catalog_sound() -> None:
    """Play on an idle Restore with no current sound starts its first catalog sound."""
    entity, rest_device = _media_entity(RestoreV4, RESTORE_CATALOG)

    entity.media_play()

    rest_device.set_sound.assert_called_once_with("432 Hz Ambience")


def test_restore_iot_without_sounds_play_does_nothing() -> None:
    """A device with no sounds to offer ignores play instead of raising IndexError."""
    entity, rest_device = _media_entity(RestoreIot)

    assert entity.sound_mode_list == []
    entity.media_play()

    assert rest_device.method_calls == []


def test_rest_iot_keeps_built_in_tracks() -> None:
    """A Rest+ lists the built-in tracks and plays them with set_audio_track."""
    entity, rest_device = _media_entity(RestIot)

    assert set(entity.sound_mode_list or []) >= RIOT_TRACK_NAMES
    entity.select_sound_mode("BrownNoise")

    rest_device.set_audio_track.assert_called_once_with(RIoTAudioTrack.BrownNoise)
    rest_device.set_sound.assert_not_called()


def test_rest_baby_keeps_built_in_tracks() -> None:
    """A Rest Baby plays its built-in tracks with set_audio_track."""
    track = next(t for t in RestBabyAudioTrack if t is not RestBabyAudioTrack.NONE)
    entity, rest_device = _media_entity(RestBaby)

    assert track.name in (entity.sound_mode_list or [])
    entity.select_sound_mode(track.name)

    rest_device.set_audio_track.assert_called_once_with(track)


def test_media_stop_rest_iot_stops_sound_only() -> None:
    """Stopping a Rest+ stops only its sound, leaving the light as it is."""
    entity, rest_device = _media_entity(RestIot)

    entity.media_stop()

    rest_device.stop_sound.assert_called_once_with()
    rest_device.turn_off.assert_not_called()


@pytest.mark.parametrize("device_class", [RestBaby, RestoreIot, RestoreV4, RestoreV5])
def test_media_stop_turns_off_devices_without_stop_sound(device_class: type) -> None:
    """Devices with no sound-only stop are turned off."""
    entity, rest_device = _media_entity(device_class)

    entity.media_stop()

    rest_device.turn_off.assert_called_once_with()
