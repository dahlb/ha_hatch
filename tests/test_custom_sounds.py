import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

CUSTOM_SOUNDS_MODULE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "ha_hatch" / "custom_sounds.py"
)
SPEC = spec_from_file_location("ha_hatch_custom_sounds", CUSTOM_SOUNDS_MODULE_PATH)
custom_sounds = module_from_spec(SPEC)
SPEC.loader.exec_module(custom_sounds)


class CustomSoundsTest(unittest.TestCase):
    def test_classic_ocean_has_complete_playable_payload(self) -> None:
        sound = custom_sounds.sound_for_mode("Classic Ocean")

        self.assertEqual(sound["id"], 10165)
        self.assertEqual(sound["title"], "Classic Ocean")
        self.assertTrue(sound["wavUrl"].endswith(".wav"))

    def test_unknown_mode_is_left_for_the_api_to_resolve(self) -> None:
        self.assertEqual(custom_sounds.sound_for_mode("Rain"), "Rain")

    def test_sound_details_prefers_custom_registry(self) -> None:
        details = custom_sounds.sound_details(
            10165,
            {
                10165: {
                    "title": "Stormy Sea",
                    "wavUrl": "https://example.com/api-name.wav",
                }
            },
        )

        self.assertEqual(
            details,
            {
                "current_sound_id": 10165,
                "current_sound_url": (
                    "https://downloads.ctfassets.net/hlsdh3zwyrtx/"
                    "2L4XgH93PtqfypPvORIFxo/"
                    "9d5eb4d5f18d182a8277a8589b27aaee/"
                    "RV4_Sleep_ClassicOcean_CGMasterV5_20221020.wav"
                ),
                "current_sound_filename": (
                    "RV4_Sleep_ClassicOcean_CGMasterV5_20221020.wav"
                ),
                "current_sound_title": "Classic Ocean",
            },
        )

    def test_sound_details_uses_api_metadata_for_other_sounds(self) -> None:
        details = custom_sounds.sound_details(
            42,
            {
                42: {
                    "title": "Rain",
                    "mp3Url": "https://example.com/sounds/Rain%20Loop.mp3",
                }
            },
        )

        self.assertEqual(details["current_sound_title"], "Rain")
        self.assertEqual(details["current_sound_filename"], "Rain Loop.mp3")


if __name__ == "__main__":
    unittest.main()
