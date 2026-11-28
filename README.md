# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dahlb/ha_hatch/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                             |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| custom\_components/ha\_hatch/\_\_init\_\_.py                     |       41 |        1 |        6 |        2 |     94% |51-\>54, 59, 67-\>72 |
| custom\_components/ha\_hatch/alarm.py                            |      173 |       24 |       92 |       17 |     82% |50, 71-72, 85, 101-105, 124, 140, 179, 181, 218, 224, 245-246, 254, 264, 268, 280, 312, 316, 320 |
| custom\_components/ha\_hatch/binary\_sensor.py                   |       26 |        1 |        2 |        1 |     93% |        58 |
| custom\_components/ha\_hatch/commands.py                         |       41 |        0 |        2 |        0 |    100% |           |
| custom\_components/ha\_hatch/config\_flow.py                     |       82 |        0 |       14 |        0 |    100% |           |
| custom\_components/ha\_hatch/const.py                            |       10 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_hatch/custom\_sounds.py                   |       82 |        0 |       26 |        0 |    100% |           |
| custom\_components/ha\_hatch/diagnostics.py                      |       37 |        0 |        8 |        1 |     98% |   68-\>75 |
| custom\_components/ha\_hatch/favorite\_slots.py                  |       77 |        0 |       24 |        1 |     99% | 235-\>223 |
| custom\_components/ha\_hatch/favorites.py                        |        9 |        0 |        2 |        0 |    100% |           |
| custom\_components/ha\_hatch/hatch\_data\_update\_coordinator.py |      236 |        4 |       58 |        3 |     98% |165, 206, 312, 315, 539-\>exit |
| custom\_components/ha\_hatch/hatch\_entity.py                    |       21 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_hatch/light.py                            |       33 |        0 |       10 |        0 |    100% |           |
| custom\_components/ha\_hatch/light\_rest\_entity.py              |       38 |        0 |        4 |        0 |    100% |           |
| custom\_components/ha\_hatch/light\_restoreiot\_entity.py        |       49 |        0 |        6 |        1 |     98% |   84-\>91 |
| custom\_components/ha\_hatch/light\_riot\_clock\_entity.py       |       67 |        4 |       14 |        2 |     93% |30-31, 49, 91 |
| custom\_components/ha\_hatch/light\_riot\_entity.py              |       46 |        0 |        8 |        1 |     98% |   74-\>76 |
| custom\_components/ha\_hatch/media\_player.py                    |       26 |        0 |        4 |        0 |    100% |           |
| custom\_components/ha\_hatch/media\_rest\_entity.py              |       74 |        3 |       18 |        4 |     92% |91, 97, 134, 144-\>exit |
| custom\_components/ha\_hatch/media\_riot\_entity.py              |      105 |        5 |       28 |        3 |     94% |112, 134, 155, 162-163 |
| custom\_components/ha\_hatch/number.py                           |       51 |        2 |        4 |        0 |     96% |   74, 105 |
| custom\_components/ha\_hatch/restore\_alarm\_slots.py            |       80 |        1 |       24 |        1 |     98% |       265 |
| custom\_components/ha\_hatch/restore\_entities.py                |      379 |        3 |       50 |        5 |     98% |187-\>189, 189-\>exit, 657-658, 666-\>668, 680, 915-\>914 |
| custom\_components/ha\_hatch/riot\_tracks.py                     |       18 |        0 |        6 |        0 |    100% |           |
| custom\_components/ha\_hatch/scene.py                            |       93 |        0 |       30 |        0 |    100% |           |
| custom\_components/ha\_hatch/select.py                           |       45 |        0 |        8 |        0 |    100% |           |
| custom\_components/ha\_hatch/sensor.py                           |      115 |       15 |       34 |        6 |     82% |93-94, 107-108, 171, 174-176, 182, 215-219, 231 |
| custom\_components/ha\_hatch/services.py                         |       77 |       17 |       34 |        9 |     71% |30, 48-49, 58, 62, 66, 101-\>94, 106-114, 128-130, 144, 149-153 |
| custom\_components/ha\_hatch/switch.py                           |      142 |       15 |       32 |        4 |     87% |98-99, 112-113, 158, 163, 192, 255-259, 271, 282, 292 |
| custom\_components/ha\_hatch/time.py                             |      115 |       14 |       30 |        3 |     84% |88-\>90, 116-117, 130-131, 218-222, 242-246 |
| **TOTAL**                                                        | **2388** |  **109** |  **578** |   **64** | **93%** |           |


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