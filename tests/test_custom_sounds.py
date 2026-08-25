import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory

CUSTOM_SOUNDS_MODULE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "ha_hatch" / "custom_sounds.py"
)
SPEC = spec_from_file_location("ha_hatch_custom_sounds", CUSTOM_SOUNDS_MODULE_PATH)
custom_sounds = module_from_spec(SPEC)
SPEC.loader.exec_module(custom_sounds)


class CustomSoundsTest(unittest.TestCase):
    def test_classic_ocean_has_complete_playable_payload(self) -> None:
        registry = custom_sounds.normalize_custom_sounds(
            {
                "ClassicOcean": {
                    "id": 10165,
                    "wav_url": (
                        "https://downloads.ctfassets.net/hlsdh3zwyrtx/"
                        "RV4_Sleep_ClassicOcean_CGMasterV5_20221020.wav"
                    ),
                }
            }
        )
        sound = custom_sounds.sound_for_mode("ClassicOcean", registry)

        self.assertEqual(sound["id"], 10165)
        self.assertEqual(sound["title"], "ClassicOcean")
        self.assertTrue(sound["wavUrl"].endswith(".wav"))

    def test_unknown_mode_is_left_for_the_api_to_resolve(self) -> None:
        self.assertEqual(custom_sounds.sound_for_mode("Rain", {}), "Rain")

    def test_sound_details_prefers_custom_registry(self) -> None:
        custom_url = (
            "https://downloads.ctfassets.net/hlsdh3zwyrtx/"
            "2L4XgH93PtqfypPvORIFxo/"
            "9d5eb4d5f18d182a8277a8589b27aaee/"
            "RV4_Sleep_ClassicOcean_CGMasterV5_20221020.wav"
        )
        details = custom_sounds.sound_details(
            10165,
            {
                10165: {
                    "title": "Stormy Sea",
                    "wavUrl": "https://example.com/api-name.wav",
                }
            },
            {
                10165: {
                    "id": 10165,
                    "title": "ClassicOcean",
                    "wavUrl": custom_url,
                }
            },
        )

        self.assertEqual(
            details,
            {
                "current_sound_id": 10165,
                "current_sound_url": custom_url,
                "current_sound_filename": (
                    "RV4_Sleep_ClassicOcean_CGMasterV5_20221020.wav"
                ),
                "current_sound_title": "ClassicOcean",
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
            {},
        )

        self.assertEqual(details["current_sound_title"], "Rain")
        self.assertEqual(details["current_sound_filename"], "Rain Loop.mp3")

    def test_invalid_entries_are_skipped(self) -> None:
        registry = custom_sounds.normalize_custom_sounds(
            {
                "Good": {"id": 1, "mp3Url": "https://example.com/good.mp3"},
                "Missing URL": {"id": 2},
                "Bad ID": {
                    "id": "three",
                    "wavUrl": "https://example.com/a.wav",
                },
                "Bad URL": {"id": 4, "wavUrl": "relative.wav"},
            }
        )

        self.assertEqual(list(registry), ["Good"])
        self.assertEqual(registry["Good"]["mp3Url"], "https://example.com/good.mp3")

    def test_duplicate_ids_are_skipped(self) -> None:
        registry = custom_sounds.normalize_custom_sounds(
            {
                "First": {"id": 1, "wavUrl": "https://example.com/first.wav"},
                "Second": {"id": 1, "wavUrl": "https://example.com/second.wav"},
            }
        )

        self.assertEqual(list(registry), ["First"])

    def test_yaml_file_is_optional(self) -> None:
        with TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.yaml"
            self.assertEqual(custom_sounds.load_custom_sounds_file(missing_path), {})

    def test_yaml_file_loads_camel_case_and_snake_case_urls(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sounds.yaml"
            path.write_text(
                """
Ocean One:
  id: 10165
  wavUrl: https://example.com/ocean.wav
Rain Two:
  id: 10166
  mp3_url: https://example.com/rain.mp3
""",
                encoding="utf-8",
            )

            registry = custom_sounds.load_custom_sounds_file(path)

        self.assertEqual(
            registry["Ocean One"]["wavUrl"], "https://example.com/ocean.wav"
        )
        self.assertEqual(registry["Rain Two"]["mp3Url"], "https://example.com/rain.mp3")

    def test_non_mapping_yaml_is_rejected(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sounds.yaml"
            path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

            self.assertEqual(custom_sounds.load_custom_sounds_file(path), {})


if __name__ == "__main__":
    unittest.main()
