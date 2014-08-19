import unittest
import requests
import json
import time

from boto import ec2
from ec2driver_config import *


class TestSpawn(unittest.TestCase):

    def setUp(self):
        print "Establishing connection with AWS"
        self.ec2_conn = ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    def test_spawn(self):
        reservation = self.ec2_conn.run_instances(aws_ami, instance_type=instance_type)
        self.instance = reservation.instances[0]
        print self.instance
        self.assertTrue(len(reservation.instances) >= 1)

    def tearDown(self):
        print "Cleanup: Destroying the instance used for testing"
        time.sleep(60)
        self.ec2_conn.terminate_instances(instance_ids=[self.instance.id])

class TestDestroy(unittest.TestCase):
    def setUp(self):
        print "Establishing connection with AWS"
        self.ec2_conn = ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    def test_destroy(self):
        reservation = self.ec2_conn.run_instances(aws_ami, instance_type=instance_type)
        print "Waiting for 120 seconds for the instance to change to running state"
        time.sleep(60)
        instance_count = len(reservation.instances)
        terminated_instances = self.ec2_conn.terminate_instances(instance_ids=[reservation.instances[0].id])
        self.assertTrue(len(terminated_instances) == 1)

if __name__ == '__main__':
    unittest.main()