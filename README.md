# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dahlb/ha_hatch/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                             |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| custom\_components/ha\_hatch/\_\_init\_\_.py                     |       35 |       35 |        6 |        0 |      0% |      3-63 |
| custom\_components/ha\_hatch/alarm.py                            |      173 |       43 |       92 |       13 |     70% |50, 67-72, 85, 101-105, 124, 140, 179, 181, 207-224, 234-246, 254, 264, 268, 280, 312, 316, 320, 330 |
| custom\_components/ha\_hatch/binary\_sensor.py                   |       26 |       26 |        2 |        0 |      0% |      3-58 |
| custom\_components/ha\_hatch/config\_flow.py                     |       52 |       52 |        6 |        0 |      0% |     3-113 |
| custom\_components/ha\_hatch/const.py                            |       10 |       10 |        0 |        0 |      0% |      4-17 |
| custom\_components/ha\_hatch/diagnostics.py                      |       36 |       36 |        8 |        0 |      0% |      3-79 |
| custom\_components/ha\_hatch/favorites.py                        |        9 |        0 |        2 |        0 |    100% |           |
| custom\_components/ha\_hatch/hatch\_data\_update\_coordinator.py |      176 |      176 |       36 |        0 |      0% |     3-353 |
| custom\_components/ha\_hatch/hatch\_entity.py                    |       21 |       21 |        0 |        0 |      0% |      3-54 |
| custom\_components/ha\_hatch/light.py                            |       28 |       28 |        8 |        0 |      0% |      3-54 |
| custom\_components/ha\_hatch/light\_rest\_entity.py              |       35 |       35 |        4 |        0 |      0% |      3-67 |
| custom\_components/ha\_hatch/light\_restoreiot\_entity.py        |       46 |       46 |        6 |        0 |      0% |     3-100 |
| custom\_components/ha\_hatch/light\_riot\_clock\_entity.py       |       64 |       64 |       14 |        0 |      0% |     3-104 |
| custom\_components/ha\_hatch/light\_riot\_entity.py              |       43 |       43 |        8 |        0 |      0% |      3-87 |
| custom\_components/ha\_hatch/media\_player.py                    |       20 |       20 |        2 |        0 |      0% |      3-55 |
| custom\_components/ha\_hatch/media\_rest\_entity.py              |       64 |       64 |       18 |        0 |      0% |     3-133 |
| custom\_components/ha\_hatch/media\_riot\_entity.py              |       76 |       76 |       14 |        0 |      0% |     3-157 |
| custom\_components/ha\_hatch/number.py                           |       48 |       48 |        4 |        0 |      0% |     3-100 |
| custom\_components/ha\_hatch/riot\_tracks.py                     |       18 |        0 |        6 |        0 |    100% |           |
| custom\_components/ha\_hatch/scene.py                            |       37 |       37 |        6 |        0 |      0% |      3-96 |
| custom\_components/ha\_hatch/select.py                           |       44 |       44 |       12 |        0 |      0% |      3-95 |
| custom\_components/ha\_hatch/sensor.py                           |      111 |      111 |       32 |        0 |      0% |     4-226 |
| custom\_components/ha\_hatch/services.py                         |       70 |       70 |       32 |        0 |      0% |     3-138 |
| custom\_components/ha\_hatch/switch.py                           |      135 |      135 |       32 |        0 |      0% |     3-282 |
| custom\_components/ha\_hatch/time.py                             |      109 |      109 |       28 |        0 |      0% |     3-238 |
| **TOTAL**                                                        | **1486** | **1329** |  **378** |   **13** | **12%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/dahlb/ha_hatch/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/dahlb/ha_hatch/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/dahlb/ha_hatch/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/dahlb/ha_hatch/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fdahlb%2Fha_hatch%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/dahlb/ha_hatch/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.