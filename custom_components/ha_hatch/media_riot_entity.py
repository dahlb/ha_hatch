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
from .commands import translate_command_errors
from .custom_sounds import CustomSound, sound_details
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

    def __init__(
        self,
        coordinator: HatchDataUpdateCoordinator,
        thing_name: str,
        custom_sounds: Mapping[str, CustomSound] | None = None,
    ) -> None:
        """Initialize the media riot entity.

        Args:
            coordinator: Coordinator that owns the device.
            thing_name: Thing name of the device.
            custom_sounds: User-defined sounds keyed by sound-mode name.
        """
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
        self._custom_sounds: dict[str, CustomSound] = dict(custom_sounds or {})
        self._custom_sounds_by_id: dict[int, CustomSound] = {
            sound["id"]: sound for sound in self._custom_sounds.values()
        }
        self._attr_sound_mode_list = sorted(
            set(
                [x.name for x in audio_data]
                + list(self.rest_device.sounds_by_name.keys())
                + list(self._program_sounds)
                + list(self._custom_sounds)
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
        sound_id = self.rest_device.sound_id
        program_sound = program_sound_name(sound_id)
        custom_sound = self._custom_sounds_by_id.get(sound_id)
        if program_sound in self._program_sounds:
            sound_mode = program_sound
        elif custom_sound is not None:
            sound_mode = custom_sound["title"]
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
        rest_device = self.rest_device
        if rest_device is None:
            return None
        # current_step / current_id only exist on RestIot; RestoreIot and others lack them
        current_id = getattr(rest_device, "current_id", None)
        return {
            "current": rest_device.current_playing,
            "current_step": getattr(rest_device, "current_step", None),
            "current_favorite": current_id,
            "current_favorite_name": next(
                (f["steps"][0]["name"] for f in rest_device.favorites if f["id"] == current_id),
                None,
            ),
            **sound_details(
                rest_device.sound_id,
                rest_device.sounds_by_id,
                self._custom_sounds_by_id,
            ),
        }

    @translate_command_errors
    def set_volume_level(self, volume: float) -> None:
        """Set the volume level (0..1)."""
        self.rest_device.set_volume(volume * 100)

    @translate_command_errors
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

    @translate_command_errors
    def select_sound_mode(self, sound_mode: str) -> None:
        """Select a sound mode."""
        _LOGGER.debug("Select sound mode: %s", sound_mode)
        # Program and custom sounds are full payloads, which play on any device.
        payload = self._program_sounds.get(sound_mode) or self._custom_sounds.get(sound_mode)
        if payload is not None:
            _LOGGER.debug("set program or custom sound: %s", sound_mode)
            self.rest_device.set_sound(payload)
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

    @translate_command_errors
    def media_stop(self) -> None:
        """Stop playback.

        A Rest+ (RestIot) stops only its sound so a light that is on stays on; other
        devices have no sound-only stop and are turned off.
        """
        if isinstance(self.rest_device, RestIot):
            _LOGGER.debug("media stop: stopping sound only")
            self.rest_device.stop_sound()
        else:
            _LOGGER.debug("media stop: turning device off")
            self.rest_device.turn_off()
