from __future__ import annotations
import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerDeviceClass,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaType,
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
    STATE_OFF,
)
from hatch_rest_api import (
    RestPlus,
    RestPlusAudioTrack,
    REST_PLUS_AUDIO_TRACKS,
    RestMini,
    RestMiniAudioTrack,
    REST_MINI_AUDIO_TRACKS,
    RestIot,
    RestoreIot,
    RIoTAudioTrack,
    REST_IOT_AUDIO_TRACKS,
)
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


class RestMediaEntity(RestEntity, MediaPlayerEntity):
    _attr_should_poll = False
    _attr_media_content_type = MediaType.MUSIC
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(self, rest_device: RestIot | RestMini | RestPlus, config_turn_on_media):
        super().__init__(rest_device, "Media Player")
        self.config_turn_on_media = config_turn_on_media

        tracks = self._get_tracks()
        self.none_track = tracks[0]
        self.default_tracks = [x.name for x in tracks[1:]]
        self.favorites = self.rest_device.favorite_names()
        self._attr_sound_mode_list = self.default_tracks + self.favorites

        # Default supported features; RestMini only has these features
        self._attr_supported_features = (
                MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.PLAY
                | MediaPlayerEntityFeature.STOP
                | MediaPlayerEntityFeature.SELECT_SOUND_MODE
                | MediaPlayerEntityFeature.VOLUME_SET
                | MediaPlayerEntityFeature.VOLUME_STEP
        )

        # RestIot and RestPlus have additional features
        if isinstance(rest_device, RestIot) or isinstance(rest_device, RestPlus):
            self._attr_supported_features = (
                self._attr_supported_features
                | MediaPlayerEntityFeature.TURN_ON
                | MediaPlayerEntityFeature.TURN_OFF
            )

    def _update_local_state(self):
        if self.platform is None or self.rest_device.audio_track is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        if isinstance(self.rest_device, RestMini) or self.rest_device.is_on:
            if self.rest_device.is_playing:
                self._attr_state = STATE_PLAYING
            else:
                self._attr_state = STATE_IDLE
        else:
            self._attr_state = STATE_OFF
        self._attr_sound_mode = self.rest_device.audio_track.name
        self._attr_volume_level = self.rest_device.volume / 100
        self._attr_device_info.update(sw_version=self.rest_device.firmware_version)
        self.async_write_ha_state()

    def _find_track(self, sound_mode=None):
        if sound_mode is None:
            sound_mode = self._attr_sound_mode

        tracks = self._get_tracks()

        return next(
            (track for track in tracks if track.name == sound_mode),
            None,
        )

    def _get_tracks(self) -> list[RestMiniAudioTrack] | list[RestPlusAudioTrack] | list[RIoTAudioTrack]:
        if isinstance(self.rest_device, RestMini):
            return REST_MINI_AUDIO_TRACKS
        elif isinstance(self.rest_device, RestIot):
            return REST_IOT_AUDIO_TRACKS

        return REST_PLUS_AUDIO_TRACKS

    def set_volume_level(self, volume: float):
        percentage = int(volume * 100)
        _LOGGER.debug(f"Setting volume to {percentage}% on {self.rest_device.device_name}")
        self.rest_device.set_volume(percentage)

    def media_play(self):
        _LOGGER.debug(f"Playing audio track [{self.rest_device.audio_track}] on {self.rest_device.device_name}")
        self.rest_device.set_audio_track(self.rest_device.audio_track)
        if self.config_turn_on_media:
            self.turn_on()

    def media_pause(self):
        _LOGGER.debug(f"Pausing audio track on {self.rest_device.device_name}")
        self.rest_device.set_audio_track(self.none_track)

    def media_stop(self):
        _LOGGER.debug(f"Stopping audio track on {self.rest_device.device_name}")
        if isinstance(self.rest_device, RestIot) or isinstance(self.rest_device, RestoreIot):
            self.rest_device.turn_off()
        else:
            self.rest_device.set_audio_track(self.none_track)

    def select_sound_mode(self, sound_mode: str):
        _LOGGER.debug(f'Setting sound mode [{sound_mode}] on {self.rest_device.device_name}')
        
        if sound_mode in self.favorites:
            _LOGGER.debug(f'Setting favorite [{sound_mode}] on {self.rest_device.device_name}')
            self.rest_device.set_favorite(sound_mode)

        elif sound_mode in self.default_tracks:
            track = self._find_track(sound_mode=sound_mode)
            _LOGGER.debug(f'Setting track [{track}] for sound_mode [{sound_mode}] on {self.rest_device.device_name}')
            if track is None:
                track = self.none_track
            self.rest_device.set_audio_track(track)
        # # TEST ONLY; commenting out for now...
        # elif sound_mode == "LULZ":
        #     _LOGGER.debug(f'Funny person, huh? Ok..')
        #     self.rest_device.set_sound_url()

        if self.config_turn_on_media:
            self.turn_on()

    def turn_off(self):
        self.media_stop()
