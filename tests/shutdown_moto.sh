#! /usr/bin/env bash

echo "Unsetting environment variable MOCK_EC2"
unset MOCK_EC2

echo "Killing moto"
ps aux | grep moto_server | grep -v grep | awk '{print $2}' | xargs kill -9
