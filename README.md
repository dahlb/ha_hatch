[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

A custom integration for Hatch Rest Mini/Plus Sound Machine. This project is mostly from looking at other core integrations

Warning ahead; this is beta phase, if you notice something missing please open an issue.

## Feature Highlights ##
- monitor device connectivity
- start and stop sound machine with variety of built-in sounds
- adjust the volume
- monitor rest plus battery level
- adjust rest plus brightness and color
- turn rest plus on and off

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

