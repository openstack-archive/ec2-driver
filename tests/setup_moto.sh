#! /usr/bin/env bash

if [ ! -d "logs" ]; then
    echo "Making logs directory"
    mkdir logs
fi

echo "Setting environment variable MOCK_EC2=True"
export MOCK_EC2=True

echo "Restarting moto"
ps aux | grep moto_server | grep -v grep | awk '{print $2}' | xargs kill -9
moto_server ec2 -p1234  > logs/moto_log.txt 2>&1 &
