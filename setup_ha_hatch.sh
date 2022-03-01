#!/bin/bash

apk -e info make
if [[ $? -eq 0 ]]; then
    echo "noop exiting"
    exit 0
fi

echo "installing and restarting"
apk add gcc g++ cmake make
pkill python3
