<img src="https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.ha_hatch.total">

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

A custom integration for Hatch Rest/Restore Sound Machines. This project is mostly from looking at other core integrations

## Tested Devices ##
- Rest Mini
- Rest+
- Rest 2nd gen
- Rest+ 2nd gen
- Restore (1st gen, product `restoreIot`)
- Restore (1st gen original, product `restore`) - experimental, see [Original Restore](#original-restore)
- Restore 2
- Restore 3
- Restore 5

## Feature Highlights ##
- monitor device connectivity
- start and stop sound machine with variety of built-in sounds (Rest mini & Rest+)
- play favorites set in the Hatch app (Rest 2nd gen, Rest+ 2nd gen, Restore 3)
- adjust the volume
- monitor battery level (Rest+ & Rest+ 2nd gen)
- adjust light brightness and color
- turn rest plus on and off
- turn clock on and off and adjust brightness (Rest+ 2nd gen/Restore 3) 
- full clock display control - separate day/night brightness, clock mode (Always On / Off at Night / Always Off), on/off schedule times, and tap-to-show (Restore 5)
- enable, disable, and edit wake times for existing alarms (Restore `restoreIot`, Restore 2, Restore 3)
- light, sound, routine step, clock, alarms on/off, and each alarm's time, days and on/off (original Restore `restore`)
- turn Toddler Lock on and off (Rest+ 2nd gen) 
- monitor device charging status (Rest+ 2nd gen)

## Installation ##
You can install this either manually copying files or using HACS. Configuration can be done on UI, you need to enter your username and password, (I know, translations are missing). 

upstream limitation https://github.com/awslabs/aws-crt-python/issues/315 is now automatically worked around thanks to code provided by https://github.com/qqaatw/

## Troubleshooting ##
If you receive an error, please go through these steps;
1. Enabled Debug Logging, at /config/integrations/integration/ha_hatch
2. Restart you home assistant to capture initialization with debug logging, then try to do what your having trouble with
3. Disable Debug Logging, at /config/integrations/integration/ha_hatch (which will download the logs)
4. Click the three dots menu for your device, at /config/integrations/integration/ha_hatch
5. Click Download Diagnostics
6. Attach both logs and diagnostics to your issue ticket.

## Original Restore ##
Hatch sold two first generation Restores, and they report different product codes to the Hatch cloud: `restoreIot` and the older `restore`. Both are supported, but differently. Once set up, the device page shows model `RestoreIot` or `Restore` respectively. The model label underneath an original reads RESTORE01 or RESTORE02.

Every control below was checked on a real original Restore before it was added.

| Entity | What it does |
|---|---|
| light `Light` | On/off, brightness, and the 22 colors from the Hatch app as effects |
| media player `Sound` | Play/stop, volume, and the 31 sounds as sound modes |
| switch `Bedtime Routine` | On starts the bedtime routine set up in the Hatch app; off stops whatever is playing |
| select `Routine Step` | Start the routine at a chosen step; shows the step playing |
| sensor `Playing` | `none`, `routine` or `remote`, with the routine step as an attribute |
| light `Clock` | Clock display on/off and brightness |
| switch `Clock 24-Hour`, select `Clock Mode`, time `Clock Turn On At` / `Clock Turn Off At` | 12/24-hour, and whether the clock turns off at night between those times |
| switch `Alarms` | All alarms on or off, like the crossed-bell button underneath |
| switch `Alarm 1`, time `Alarm 1 Wake Time`, sensor `Alarm 1 Repeat` (one set per alarm) | Turn an alarm on or off, change its wake time, and see its repeat days. Its sound, volume and sunrise settings are attributes |
| sensors `Firmware Version`, `Wifi Signal`, binary sensor `Wifi` | Diagnostics |

How it behaves:
* **Light and sound:** the Restore only lights up or plays while it is in a playback mode. Turning the light or sound on while nothing plays starts it, and turning off the last one stops it.
* **Volume:** the Restore resets its volume to 0 whenever playback stops. The `Sound` player remembers the last volume and starts the next sound at it, and shows that volume while idle.
* **Alarm edits:** changing an alarm's time or days saves it as a new alarm, exactly as the Hatch app does, because the Restore only reloads an alarm whose id changed. The `Alarm N` entities keep their names and entity ids through this, including after edits made in the Hatch app. Alarms are numbered by time of day when first seen.
* **Repeat days:** change them with the `ha_hatch.set_alarm_weekdays` action, targeting any of the alarm's entities, for example `weekdays: [monday, wednesday]`, or an empty list for a one-time alarm.
* **Alarm changes made in the Hatch app** show up within 10 minutes, or straight away after reloading the integration.

Not available yet: changing an alarm's sound, volume or sunrise color, and creating or deleting alarms. The clock's "always off" mode does nothing on this model; turn the `Clock` light off instead.

If something does not work, Download Diagnostics: it includes the device's full state under `shadow_state` and its alarms under `restore_alarms`, with headphone pairing details redacted. The protocol behind all of this is written up in [hatch_rest_api docs/restore.md](https://github.com/dahlb/hatch_rest_api/blob/main/docs/restore.md).

## Usage ##
You can now use the following services:
* Rest+ 2nd gen: activate scene to start a defined favorite
  * scenes for new, edited, reordered or deleted favorites follow within about an hour (when the integration logs in again); reload the integration to pick them up right away
  * editing or reordering a favorite in the Hatch app gives it a new Hatch id, but its scene keeps its entity id, so dashboards and automations keep working; the `hatch_favorite_id` attribute shows the current id
* Restore (`restoreIot`)/Restore 2/Restore 3: use the alarm switch to enable or disable an existing alarm (for the original Restore, see [Original Restore](#original-restore))
  * use the alarm wake time entity to change when the alarm sound starts; the sunrise light start shifts with it
  * when Hatch omits an alarm `endTime`, wake time is derived from `startTime` plus the alarm sunrise duration
  * automations can set wake time with the built-in `time.set_value` action, for example `time: "06:45:00"`
  * automations and Developer Tools can set repeat days with the `ha_hatch.set_alarm_weekdays` action
  * alarm changes made in the Hatch app are refreshed automatically every 10 minutes; reload the integration to see them immediately
  * alarm creation, alarm deletion, and alarm sound/light editing are not supported
* Media player: Select sound mode
  * Possible options here are: Stream, PinkNoise, Dryer, Ocean, Wind, Rain, Bird, Crickets, Brahms, Twinkle, RockABye
  * Restore 2 and Restore 3 offer the free sounds from their own Hatch sound library instead of the built-in Rest tracks, which they can't play
  * Rest 2nd gen and Rest+ 2nd gen also offer the Time to Rise and Time for Bed tracks as `TimeToRise.<Name>` and `TimeForBed.<Name>` (for example `TimeToRise.YukiSaysGoodMorning`), and show these names as the sound mode while a Hatch app routine plays them
  * Rest+, Rest Baby and Restore 2/3 also offer any sounds defined in `hatch_custom_sounds.yaml`; see [Custom Sounds](#custom-sounds)
* Media player: Set volume
* Media player: Play
* Media player: Stop
* Light: Turn on
  * Possible values to modify:
    * brightness
    * hs_color
    * rgb_color
    * xy_color
* Light: Turn off

Here are the basic colors from the app:
* Orange
  * hs_color: 25.767, 69.658
  * rgb_color: 234, 141, 71
  * xy_color: 0.547, 0.379
* Dark blue
  * hs_color: 212.368, 67.556
  * rgb_color: 73, 143, 225
  * xy_color: 0.173, 0.197
* Light blue
  * hs_color: 187.586, 80.93
  * rgb_color: 41, 193, 215
  * xy_color: 0.158, 0.301
* Green
  * hs_color: 153.051, 56.19
  * rgb_color: 92, 210, 157
  * xy_color: 0.208, 0.441
* Pink
  * hs_color: 330.811, 60.163
  * rgb_color: 246, 98, 170
  * xy_color: 0.476, 0.248

## Custom Sounds ##
Additional sounds can be defined outside the integration in
`/config/hatch_custom_sounds.yaml` (see `hatch_custom_sounds.example.yaml`). The
YAML key becomes the sound-mode name. Each sound needs a positive integer `id`
and either a WAV or MP3 URL. Both camel-case (`wavUrl`/`mp3Url`) and snake-case
(`wav_url`/`mp3_url`) URL keys are supported.

```yaml
ClassicOcean:
  id: 10165
  wav_url: "https://downloads.ctfassets.net/hlsdh3zwyrtx/2L4XgH93PtqfypPvORIFxo/9d5eb4d5f18d182a8277a8589b27aaee/RV4_Sleep_ClassicOcean_CGMasterV5_20221020.wav"
```

Reload the integration or restart Home Assistant after changing the file.
Invalid entries are ignored and described in the Home Assistant log. While a
sound plays, the media player shows its `current_sound_id`,
`current_sound_url`, `current_sound_filename` and `current_sound_title`
attributes.

***


[ha_hatch]: https://github.com/dahlb/ha_hatch
[commits-shield]: https://img.shields.io/github/commit-activity/y/dahlb/ha_hatch.svg?style=for-the-badge
[commits]: https://github.com/dahlb/ha_hatch/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/dahlb/ha_hatch.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Bren%20Dahl%20%40dahlb-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/dahlb/ha_hatch.svg?style=for-the-badge
[releases]: https://github.com/dahlb/ha_hatch/releases
[buymecoffee]: https://www.buymeacoffee.com/dahlb
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
