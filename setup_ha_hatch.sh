#!/bin/bash

pip install hatch-rest-api==1.12.1 -f https://qqaatw.github.io/aws-crt-python-musllinux/
#exit 0

# old version for below 1.10.0 release

apk -e info make
if [[ $? -eq 0 ]]; then
    echo "noop exiting"
    exit 0
fi

echo "installing and restarting"
apk add gcc g++ cmake make
pkill python3
