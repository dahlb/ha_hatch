import logging
from typing import Any
from collections.abc import Mapping

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerDeviceClass, MediaPlayerState,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaType
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
)

from . import HatchDataUpdateCoordinator
from .hatch_entity import HatchEntity
from hatch_rest_api import REST_IOT_AUDIO_TRACKS

_LOGGER = logging.getLogger(__name__)


class MediaRiotEntity(HatchEntity, MediaPlayerEntity):
    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(self, coordinator: HatchDataUpdateCoordinator, thing_name: str):
        super().__init__(coordinator=coordinator, thing_name=thing_name, entity_type="Media Player")
        self._attr_sound_mode_list = sorted([x.name for x in REST_IOT_AUDIO_TRACKS[1:]] + self.rest_device.sounds_by_name.keys())
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
        if self.rest_device.is_playing:
            return STATE_PLAYING
        else:
            return STATE_IDLE

    @property
    def sound_mode(self) -> str | None:
        if self.rest_device.audio_track is not None:
            return self.rest_device.audio_track.name
        else:
            sound = self.rest_device.sounds_by_id.get(self.rest_device.sound_id) or {}
            return sound.get('title') or None

    @property
    def volume_level(self) -> float | None:
        return self.rest_device.volume / 100

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        return {
            "current": self.rest_device.current_playing,
            "current_step": self.rest_device.current_step,
            "current_favorite": self.rest_device.current_id,
            "current_favorite_name": next((
                f["steps"][0]["name"] for f
                in self.rest_device.favorites
                if f["id"] == self.rest_device.current_id
            ), None),
        }

    def set_volume_level(self, volume):
        self.rest_device.set_volume(volume * 100)

    def media_play(self) -> None:
        self.select_sound_mode(self._attr_sound_mode_list[0])

    def _find_track(self, track_name) -> str | None:
        if track_name is None:
            track_name = self.sound_mode
        return next(
            (track for track in REST_IOT_AUDIO_TRACKS if track.name == track_name),
            None,
        )

    def select_sound_mode(self, sound_mode: str) -> None:
        track = self._find_track(track_name=sound_mode)
        if track is None:
            self.rest_device.set_sound(sound_mode)
        else:
            self.rest_device.set_audio_track(track)

    def media_stop(self):
        self.rest_device.turn_off()
