#! /usr/bin/env bash

echo "Unsetting environment variable TEST"
unset TEST

echo "Killing moto"
ps aux | grep moto_server | grep -v grep | awk '{print $2}' | xargs kill -9
