# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dahlb/ha_hatch/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                             |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| custom\_components/ha\_hatch/\_\_init\_\_.py                     |       35 |       22 |        6 |        0 |     32% |19-20, 25-45, 50, 55-63 |
| custom\_components/ha\_hatch/alarm.py                            |      173 |       43 |       92 |       13 |     70% |50, 67-72, 85, 101-105, 124, 140, 179, 181, 207-224, 234-246, 254, 264, 268, 280, 312, 316, 320, 330 |
| custom\_components/ha\_hatch/binary\_sensor.py                   |       26 |       26 |        2 |        0 |      0% |      3-58 |
| custom\_components/ha\_hatch/config\_flow.py                     |       51 |       51 |        6 |        0 |      0% |     3-112 |
| custom\_components/ha\_hatch/const.py                            |       10 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_hatch/diagnostics.py                      |       36 |       36 |        8 |        0 |      0% |      3-79 |
| custom\_components/ha\_hatch/favorites.py                        |        9 |        0 |        2 |        0 |    100% |           |
| custom\_components/ha\_hatch/hatch\_data\_update\_coordinator.py |      176 |      126 |       36 |        0 |     24% |56-63, 83-100, 106-120, 123-124, 128-131, 142-147, 150-153, 160-190, 193-199, 205-207, 218-235, 246-255, 258-261, 268-338, 342-349, 353 |
| custom\_components/ha\_hatch/hatch\_entity.py                    |       21 |        1 |        0 |        0 |     95% |        54 |
| custom\_components/ha\_hatch/light.py                            |       28 |       28 |        8 |        0 |      0% |      3-54 |
| custom\_components/ha\_hatch/light\_rest\_entity.py              |       35 |       35 |        4 |        0 |      0% |      3-67 |
| custom\_components/ha\_hatch/light\_restoreiot\_entity.py        |       46 |       46 |        6 |        0 |      0% |     3-100 |
| custom\_components/ha\_hatch/light\_riot\_clock\_entity.py       |       64 |       64 |       14 |        0 |      0% |     3-104 |
| custom\_components/ha\_hatch/light\_riot\_entity.py              |       43 |       43 |        8 |        0 |      0% |      3-87 |
| custom\_components/ha\_hatch/media\_player.py                    |       20 |       20 |        2 |        0 |      0% |      3-55 |
| custom\_components/ha\_hatch/media\_rest\_entity.py              |       64 |       64 |       18 |        0 |      0% |     3-133 |
| custom\_components/ha\_hatch/media\_riot\_entity.py              |       85 |       16 |       22 |        4 |     79% |82-84, 92, 94-95, 105, 111-112, 128, 134-135, 147-149, 165 |
| custom\_components/ha\_hatch/number.py                           |       48 |       48 |        4 |        0 |      0% |     3-100 |
| custom\_components/ha\_hatch/riot\_tracks.py                     |       18 |        0 |        6 |        0 |    100% |           |
| custom\_components/ha\_hatch/scene.py                            |       37 |       37 |        6 |        0 |      0% |      3-96 |
| custom\_components/ha\_hatch/select.py                           |       38 |        3 |        4 |        0 |     93% |     43-50 |
| custom\_components/ha\_hatch/sensor.py                           |      111 |      111 |       32 |        0 |      0% |     4-226 |
| custom\_components/ha\_hatch/services.py                         |       70 |       52 |       32 |        0 |     18% |24-30, 41-44, 51-67, 75-104, 114-138 |
| custom\_components/ha\_hatch/switch.py                           |      129 |       74 |       30 |        0 |     35% |35-117, 132, 137, 141, 145, 159, 164, 168, 172, 220-229, 233-237, 242, 247-250, 255, 259, 263, 266-270, 274 |
| custom\_components/ha\_hatch/time.py                             |      108 |       56 |       28 |        0 |     40% |62-139, 193-201, 205-209, 214, 219, 224, 228-232, 236 |
| **TOTAL**                                                        | **1481** | **1002** |  **376** |   **17** | **30%** |           |


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