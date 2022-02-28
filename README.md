[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

A custom integration for Hatch Rest Mini Sound Machine. This project is mostly from looking at other core integrations

Warning ahead; this is alpha phase, if you notice something missing please open an issue.

## Feature Highlights ##
- start and stop sound machine with variety of built in sounds
- adjust the volume

## Installation ##
You can install this either manually copying files or using HACS. Configuration can be done on UI, you need to enter your username and password, (I know, translations are missing). 

Due to upstream limitation https://github.com/awslabs/aws-crt-python/issues/315

if you use alpine linux for home assistant like the official docker image; run `apk add gcc g++ cmake make`

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

