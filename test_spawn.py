import unittest
import requests
import json
import time

from novaclient.v1_1 import client
from credentials import get_nova_creds

from boto import ec2
from ec2driver_config import *


class TestSpawn(unittest.TestCase):

    def setUp(self):
        print "Establishing connection with AWS"
        self.ec2_conn = ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        self.creds = get_nova_creds()
    
    # @unittest.skip("For fun")
    def test_spawn(self):
        print "Spawning an instance"
        nova = client.Client(**self.creds)
        image = nova.images.find(name="cirros-0.3.1-x86_64-uec")
        flavor = nova.flavors.find(name="m1.tiny")
        self.server = nova.servers.create(name = "cirros-test",
                        image = image.id,
                        flavor = flavor.id)
        time.sleep(15)
        
        instance = self.ec2_conn.get_only_instances(instance_ids=[self.server.metadata['ec2_id']], filters=None, dry_run=False, max_results=None)
        
        self.assertTrue(len(instance) == 1)
    
    def tearDown(self):
        print "Cleanup: Destroying the instance used for testing"
        time.sleep(15)
        self.server.delete()
        
class TestDestroy(unittest.TestCase):
    def setUp(self):
        print "Establishing connection with AWS"
        self.ec2_conn = ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        self.creds = get_nova_creds()
    
    # @unittest.skip("For fun")
    def test_destroy(self):
        print "Spawning an instance"
        nova = client.Client(**self.creds)
        image = nova.images.find(name="cirros-0.3.1-x86_64-uec")
        flavor = nova.flavors.find(name="m1.tiny")
        server = nova.servers.create(name = "cirros-test",
                        image = image.id,
                        flavor = flavor.id)
        time.sleep(20)
        ec2_id = server.metadata['ec2_id']
        server.delete()

        time.sleep(10)
        instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False, max_results=None)
        
        shutting_down_state_code = 32
        self.assertEquals(instance[0].state_code, shutting_down_state_code)

if __name__ == '__main__':
    unittest.main()