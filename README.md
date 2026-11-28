# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/dahlb/ha_hatch/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                             |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| custom\_components/ha\_hatch/\_\_init\_\_.py                     |       41 |       24 |        6 |        0 |     36% |26-27, 32-54, 59, 64-72 |
| custom\_components/ha\_hatch/alarm.py                            |      173 |       39 |       92 |       15 |     72% |50, 67-72, 85, 101-105, 124, 140, 179, 181, 210-224, 237-246, 254, 264, 268, 280, 312, 316, 320, 330 |
| custom\_components/ha\_hatch/binary\_sensor.py                   |       26 |        4 |        2 |        0 |     79% | 51, 56-58 |
| custom\_components/ha\_hatch/config\_flow.py                     |       51 |       51 |        6 |        0 |      0% |     3-112 |
| custom\_components/ha\_hatch/const.py                            |       10 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_hatch/custom\_sounds.py                   |       82 |        0 |       26 |        0 |    100% |           |
| custom\_components/ha\_hatch/diagnostics.py                      |       37 |       10 |        8 |        1 |     67% |     54-75 |
| custom\_components/ha\_hatch/favorite\_slots.py                  |       77 |        0 |       24 |        1 |     99% | 235-\>223 |
| custom\_components/ha\_hatch/favorites.py                        |        9 |        0 |        2 |        0 |    100% |           |
| custom\_components/ha\_hatch/hatch\_data\_update\_coordinator.py |      237 |      130 |       58 |        1 |     43% |87-103, 123-140, 146-160, 163-164, 168-171, 182-187, 190-193, 200-230, 233-239, 245-247, 258-275, 286-295, 298-301, 308-378, 382-389, 538-\>exit, 543 |
| custom\_components/ha\_hatch/hatch\_entity.py                    |       21 |        0 |        0 |        0 |    100% |           |
| custom\_components/ha\_hatch/light.py                            |       33 |        6 |       10 |        3 |     74% |34, 42-45, 55-59 |
| custom\_components/ha\_hatch/light\_rest\_entity.py              |       35 |       16 |        4 |        0 |     49% |26-27, 32, 37, 42, 50-63, 67 |
| custom\_components/ha\_hatch/light\_restoreiot\_entity.py        |       46 |       26 |        6 |        0 |     38% |32-33, 38-44, 49, 54, 63-96, 100 |
| custom\_components/ha\_hatch/light\_riot\_clock\_entity.py       |       64 |       39 |       14 |        0 |     32% |21-30, 41-48, 60, 64-65, 70, 75-80, 84-99, 103-104 |
| custom\_components/ha\_hatch/light\_riot\_entity.py              |       43 |       23 |        8 |        0 |     39% |31-32, 37-42, 47, 52, 60-77, 87 |
| custom\_components/ha\_hatch/media\_player.py                    |       26 |        0 |        4 |        0 |    100% |           |
| custom\_components/ha\_hatch/media\_rest\_entity.py              |       64 |       30 |       18 |        1 |     43% |54-56, 70-74, 79, 84, 87-94, 101, 105-107, 111, 115, 119-124, 128, 132-133 |
| custom\_components/ha\_hatch/media\_riot\_entity.py              |      100 |       11 |       28 |        4 |     87% |99-101, 111, 115-116, 126, 133, 153, 159-160 |
| custom\_components/ha\_hatch/number.py                           |       48 |        8 |        4 |        1 |     83% |32-38, 59, 68, 72, 87, 96, 100 |
| custom\_components/ha\_hatch/restore\_alarm\_slots.py            |       80 |        1 |       24 |        1 |     98% |       265 |
| custom\_components/ha\_hatch/restore\_entities.py                |      357 |        3 |       50 |        5 |     98% |185-\>187, 187-\>exit, 634-635, 643-\>645, 657, 889-\>888 |
| custom\_components/ha\_hatch/riot\_tracks.py                     |       18 |        0 |        6 |        0 |    100% |           |
| custom\_components/ha\_hatch/scene.py                            |       91 |        0 |       30 |        0 |    100% |           |
| custom\_components/ha\_hatch/select.py                           |       43 |        0 |        8 |        1 |     98% |   52-\>51 |
| custom\_components/ha\_hatch/sensor.py                           |      115 |       46 |       34 |        7 |     54% |54, 58, 61-\>52, 80, 84-104, 107-108, 125, 145, 150, 163, 170-176, 181-183, 203-211, 215-219, 224, 229-232, 237, 241 |
| custom\_components/ha\_hatch/services.py                         |       75 |       33 |       34 |        6 |     51% |28-34, 45-48, 57, 61, 65, 85-114, 126-128, 142, 147-151 |
| custom\_components/ha\_hatch/switch.py                           |      133 |       51 |       32 |        9 |     58% |46, 50, 54-57, 62, 65-\>44, 85, 89-108, 111-112, 129, 147, 152, 156, 160, 174, 179, 183, 187, 235-244, 248-252, 257, 262-265, 270, 274, 278, 281-285, 289 |
| custom\_components/ha\_hatch/time.py                             |      112 |       35 |       30 |        7 |     63% |69-70, 80-\>66, 87-\>89, 102, 106-126, 129-130, 147, 204-212, 216-220, 225, 230, 235, 239-243, 247 |
| **TOTAL**                                                        | **2247** |  **586** |  **568** |   **63** | **71%** |           |


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