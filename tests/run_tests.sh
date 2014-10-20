#! /usr/bin/env bash

#source ~/devstack/openrc admin
sh ~/devstack/openrc admin

export TEST=True
ps aux | grep 'screen\|nova\|cinder\|horizon' | grep -v grep | awk '{print $2}' | xargs kill -9
ps aux | grep moto_server | grep -v grep | awk '{print $2}' | xargs kill -9

echo "START MOTO"
moto_server ec2 -p1234 &

echo "START OPENSTACK"
bash ../start_openstack.sh
#sh ../start_openstack.sh > testlog.txt 2>&1 &

#/usr/bin/env bash ~/devstack/rejoin-stack.sh &

sleep 10

echo "START TESTS"
nosetests -s test_ec2driver.py > test_output.txt 2>&1
#nosetests -s test_ec2driver.py

echo "KILL EVERYTHING"
ps aux | grep 'screen\|nova\|cinder\|horizon' | grep -v grep | awk '{print $2}' | xargs kill -9
#ps aux | grep moto_server | grep -v grep | awk '{print $2}' | xargs kill -9
unset TEST
echo 'DONE'