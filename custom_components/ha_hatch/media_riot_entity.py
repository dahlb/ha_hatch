"""Media player entity for Hatch Rest+ (riot) devices."""

from collections.abc import Mapping
import logging
from typing import Any

from hatch_rest_api import (
    REST_BABY_AUDIO_TRACKS,
    REST_IOT_AUDIO_TRACKS,
    RestBaby,
    RestBabyAudioTrack,
    RestIot,
    RIoTAudioTrack,
)
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerState,
)
from homeassistant.components.media_player.const import MediaPlayerEntityFeature, MediaType
from homeassistant.const import STATE_IDLE, STATE_PLAYING

from . import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity
from .riot_tracks import PROGRAM_SOUNDS, program_sound_name

_LOGGER = logging.getLogger(__name__)


def _find_track(track_name: str | None) -> RIoTAudioTrack | None:
    return next(
        (track for track in REST_IOT_AUDIO_TRACKS if track.name == track_name),
        None,
    )


def _find_rest_baby_track(track_name: str | None) -> RestBabyAudioTrack | None:
    return next(
        (track for track in REST_BABY_AUDIO_TRACKS if track.name == track_name),
        None,
    )


class MediaRiotEntity(HatchEntity, MediaPlayerEntity):
    """Media riot entity."""

    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str) -> None:
        """Initialize the media riot entity."""
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Media Player")
        if isinstance(self.rest_device, RestBaby):
            audio_data = REST_BABY_AUDIO_TRACKS[1:]
        elif isinstance(self.rest_device, RestIot):
            audio_data = REST_IOT_AUDIO_TRACKS[1:]
        else:
            # Restore devices have no set_audio_track and only play sounds from their own
            # catalog (sounds_by_name), so the built-in Rest tracks aren't offered.
            audio_data = []
        self._program_sounds = PROGRAM_SOUNDS if isinstance(self.rest_device, RestIot) else {}
        self._attr_sound_mode_list = sorted(
            set(
                [x.name for x in audio_data]
                + list(self.rest_device.sounds_by_name.keys())
                + list(self._program_sounds)
            )
        )
        self._attr_supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.SELECT_SOUND_MODE
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )
        self._attr_extra_state_attributes = {}

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the media player state."""
        if self.rest_device.is_playing:
            return STATE_PLAYING
        return STATE_IDLE

    @property
    def sound_mode(self) -> str | None:
        """Return the current sound mode."""
        _LOGGER.debug("looking up sound mode")
        program_sound = program_sound_name(self.rest_device.sound_id)
        if program_sound in self._program_sounds:
            sound_mode = program_sound
        elif hasattr(self.rest_device, "audio_track") and self.rest_device.audio_track is not None:
            _LOGGER.debug("Audio track found: %s", self.rest_device.audio_track)
            sound_mode = self.rest_device.audio_track.name
        else:
            sound = self.rest_device.sounds_by_id.get(self.rest_device.sound_id) or {}
            sound_mode = sound.get("title") or None
        _LOGGER.debug("sound mode: %s", sound_mode)
        return sound_mode

    @property
    def volume_level(self) -> float | None:
        """Return the volume level (0..1)."""
        return self.rest_device.volume / 100

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return extra state attributes."""
        # current_step / current_id only exist on RestIot; RestoreIot and others lack them
        current_id = getattr(self.rest_device, "current_id", None)
        return {
            "current": self.rest_device.current_playing,
            "current_step": getattr(self.rest_device, "current_step", None),
            "current_favorite": current_id,
            "current_favorite_name": next(
                (
                    f["steps"][0]["name"]
                    for f in self.rest_device.favorites
                    if f["id"] == current_id
                ),
                None,
            ),
        }

    def set_volume_level(self, volume: float) -> None:
        """Set the volume level (0..1)."""
        self.rest_device.set_volume(volume * 100)

    def media_play(self) -> None:
        """Start playback."""
        _LOGGER.debug("media play")
        if self.rest_device.is_playing:
            _LOGGER.debug("media player already playing")
            return
        new_sound_mode = self.sound_mode or next(iter(self._attr_sound_mode_list or []), None)
        if new_sound_mode is None:
            _LOGGER.debug("no sound available to play")
            return
        _LOGGER.debug("selecting sound mode of %s", new_sound_mode)
        self.select_sound_mode(new_sound_mode)

    def select_sound_mode(self, sound_mode: str) -> None:
        """Select a sound mode."""
        _LOGGER.debug("Select sound mode: %s", sound_mode)
        if sound_mode in self._program_sounds:
            _LOGGER.debug("set program sound: %s", sound_mode)
            self.rest_device.set_sound(self._program_sounds[sound_mode])
            return
        if isinstance(self.rest_device, RestBaby):
            track = _find_rest_baby_track(track_name=sound_mode)
        elif isinstance(self.rest_device, RestIot):
            track = _find_track(track_name=sound_mode)
        else:
            track = None
        if track is None:
            _LOGGER.debug("No track found")
            self.rest_device.set_sound(sound_mode)
        else:
            _LOGGER.debug("set audio track: %s", track)
            self.rest_device.set_audio_track(track)

    def media_stop(self) -> None:
        """Stop playback."""
        self.rest_device.turn_off()
