import os
import unittest
import time

from boto.regioninfo import RegionInfo
from novaclient.v1_1 import client
from boto import ec2

from ..credentials import get_nova_creds
from ..ec2driver_config import *

class EC2TestBase(unittest.TestCase):
    @staticmethod
    def sleep_if_ec2_not_mocked(seconds):
        if not os.environ.get('MOCK_EC2'):
            time.sleep(seconds)


    @classmethod
    def setUp(self):
        print "Establishing connection with AWS"

        region = RegionInfo(name=aws_region, endpoint=aws_endpoint)
        self.ec2_conn = ec2.EC2Connection(aws_access_key_id=aws_access_key_id,
                                         aws_secret_access_key=aws_secret_access_key,
                                         host=host,
                                         port=port,
                                         region = region,
                                         is_secure=secure)

        self.creds = get_nova_creds()
        self.nova = client.Client(**self.creds)

        # nova client for cinder
        self.creds['service_type'] = 'volume'
        self.nova_volume = client.Client(**self.creds)

        self.servers = []
        self.volumes = []

    @classmethod
    def tearDown(self):
        print "Cleanup: Destroying the instance used for testing"
        for instance in self.servers:
            instance.delete()

        # wait for all instances to completely shut down and detach volumes if any
        self.sleep_if_ec2_not_mocked(120)

        for volume in self.volumes:
            volume.delete()

    def spawn_ec2_instance(self):
        print "aws_region: " + aws_region

        print "Spawning an instance"
        image = self.nova.images.find(name="cirros-0.3.1-x86_64-uec")
        flavor = self.nova.flavors.find(name="m1.tiny")
        server = self.nova.servers.create(
            name="cirros-test", image=image.id, flavor=flavor.id)
        instance = self.nova.servers.get(server.id)
        while instance.status != 'ACTIVE':
            EC2TestBase.sleep_if_ec2_not_mocked(10)
            instance = self.nova.servers.get(server.id)
        self.servers.append(instance)
        return instance, server.id