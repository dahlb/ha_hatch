import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    DEVICE_CLASS_SPEAKER,
)
from homeassistant.components.media_player.const import (
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_STOP,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
    SUPPORT_TURN_ON,
    SUPPORT_TURN_OFF,
    MEDIA_TYPE_MUSIC,
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_PLAYING,
    STATE_OFF,
)
from hatch_rest_api import RestIot
from .rest_entity import RestEntity

_LOGGER = logging.getLogger(__name__)


class RiotMediaEntity(RestEntity, MediaPlayerEntity):
    _attr_should_poll = False
    _attr_media_content_type = MEDIA_TYPE_MUSIC
    _attr_device_class = DEVICE_CLASS_SPEAKER

    def __init__(self, rest_device: RestIot):
        super().__init__(rest_device, "Media Player")
        self._attr_sound_mode_list = self.rest_device.favorite_names()
        self._attr_supported_features = (
            SUPPORT_PLAY
            | SUPPORT_STOP
            | SUPPORT_SELECT_SOUND_MODE
            | SUPPORT_VOLUME_SET
            | SUPPORT_VOLUME_STEP
        )

    def _update_local_state(self):
        if self.platform is None:
            return
        _LOGGER.debug(f"updating state:{self.rest_device}")
        if self.rest_device.is_playing:
            self._attr_state = STATE_PLAYING
        else:
            self._attr_state = STATE_IDLE
        self._attr_sound_mode = self.rest_device.audio_track
        self._attr_volume_level = self.rest_device.volume / 100
        self._attr_device_info.update(sw_version=self.rest_device.firmware_version)
        self.async_write_ha_state()

    def set_volume_level(self, volume):
        self.rest_device.set_volume(volume * 100)

    def media_play(self):
        self.rest_device.set_favorite(self._attr_sound_mode_list[0])

    def select_sound_mode(self, sound_mode: str):
        self.rest_device.set_favorite(sound_mode)

    def media_stop(self):
        self.rest_device.turn_off()
