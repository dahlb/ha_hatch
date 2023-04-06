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

Warning ahead; this is beta phase, if you notice something missing please open an issue.


## Feature Highlights ##
- monitor device connectivity
- start and stop sound machine with variety of built-in sounds (Rest mini & Rest+)
- play favorites set in the Hatch app (Rest 2nd gen & Rest+ 2nd gen)
- adjust the volume
- monitor battery level (Rest+ & Rest+ 2nd gen)
- adjust light brightness and color
- turn rest plus on and off
- turn clock on and off and adjust bightness (Rest+ 2nd gen) 
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
