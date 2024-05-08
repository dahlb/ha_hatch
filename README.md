[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

A custom integration for Hatch Rest Sound Machines. This project is mostly from looking at other core integrations

## Tested Devices ##
- Rest Mini
- Rest+
- Rest 2nd gen
- Rest+ 2nd gen


## Feature Highlights ##
- monitor device connectivity
- start and stop sound machine with variety of built-in sounds (Rest mini & Rest+)
- play favorites set in the Hatch app (Rest 2nd gen & Rest+ 2nd gen)
- adjust the volume
- monitor battery level (Rest+ & Rest+ 2nd gen)
- adjust light brightness and color
- turn rest plus on and off
- turn clock on and off and adjust brightness (Rest+ 2nd gen) 
- turn Toddler Lock on and off (Rest+ 2nd gen) 
- monitor device charging status (Rest+ 2nd gen)

## Installation ##
You can install this either manually copying files or using HACS. Configuration can be done on UI, you need to enter your username and password, (I know, translations are missing). 

upstream limitation https://github.com/awslabs/aws-crt-python/issues/315 is now automatically worked around thanks to code provided by https://github.com/qqaatw/

## Troubleshooting ##
If you receive an error while trying to login, please go through these steps;
1. You can enable logging for this integration specifically and share your logs, so I can have a deep dive investigation. To enable logging, update your `configuration.yaml` like this, we can get more information in Configuration -> Logs page
```
logger:
  default: warning
  logs:
    custom_components.ha_hatch: debug
    hatch_rest_api: debug
```


## Usage ##
You can now use the following services:
* Rest+ 2nd gen: activate scene to start a defined favorite
  * if you add new favorites reload the integration to update available scenes or restart ha
* Media player: Select sound mode
  * Possible options here are: Stream, PinkNoise, Dryer, Ocean, Wind, Rain, Bird, Crickets, Brahms, Twinkle, RockABye
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

