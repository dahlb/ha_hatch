import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerDeviceClass,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaType
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
)
from hatch_rest_api import RestIot, RestoreIot, RIoTAudioTrack, REST_IOT_AUDIO_TRACKS
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


class RiotMediaEntity(RestEntity, MediaPlayerEntity):
    _attr_should_poll = False
    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(self, rest_device: RestIot | RestoreIot):
        super().__init__(rest_device, "Media Player")
        self._attr_sound_mode_list = [x.name for x in REST_IOT_AUDIO_TRACKS[1:]]
        self._attr_supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.SELECT_SOUND_MODE
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )
        sources = []
        for favorite in self.rest_device.favorites:
            sources.append(f"{favorite['name']}-{favorite['id']}")
            for step in favorite['steps']:
                sources.append(f"{step['name']}-{favorite['id']}")

        self._attr_extra_state_attributes = {
            "sources": set(sources)
        }

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        if self.rest_device.is_playing:
            self._attr_state = STATE_PLAYING
        else:
            self._attr_state = STATE_IDLE
        self._attr_sound_mode = self.rest_device.audio_track.name
        self._attr_volume_level = self.rest_device.volume / 100
        self._attr_device_info.update(sw_version=self.rest_device.firmware_version)
        self.schedule_update_ha_state()

    def set_volume_level(self, volume):
        self.rest_device.set_volume(volume * 100)

    def media_play(self):
        self.rest_device.set_favorite(self._attr_sound_mode_list[0])

    def _find_track(self, track_name) -> str | None:
        if track_name is None:
            track_name = self._attr_sound_mode
        return next(
            (track for track in REST_IOT_AUDIO_TRACKS if track.name == track_name),
            None,
        )

    def select_sound_mode(self, sound_mode: str) -> None:
        track = self._find_track(track_name=sound_mode)
        if track is None:
            track = RIoTAudioTrack.NONE
        self.rest_device.set_audio_track(track)

    def _find_source(self, source: str) -> str:
        for favorite in self.rest_device.favorites:
            if favorite['name'] == source or favorite['id'] == source or favorite['steps'][0]['name'] == source:
                return f"{favorite['name']}-{favorite['id']}"

    def select_source(self, source: str) -> None:
        if '-' not in source:
            source = self._find_source(source)
            _LOGGER.debug(f"source missing -, found {source}")
        if source is not None and '-' in source:
            _LOGGER.debug(f"setting source: {source}")
            self.rest_device.set_favorite(source)
        _LOGGER.debug(f"source not found for {source}")

    def media_stop(self):
        self.rest_device.set_audio_track(RIoTAudioTrack.NONE)
