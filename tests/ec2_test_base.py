import unittest
import time
from boto.exception import EC2ResponseError

from boto.regioninfo import RegionInfo
import datetime
from novaclient.v1_1 import client
from boto import ec2

from ..credentials import get_nova_creds
from ..ec2driver_config import *


class EC2TestBase(unittest.TestCase):
    @staticmethod
    def sleep_if_ec2_not_mocked(seconds):
        if not os.environ.get('MOCK_EC2'):
            time.sleep(seconds)

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

    def tearDown(self):
        print "Cleanup: Destroying the instance used for testing"
        for instance in self.servers:
            self.destroy_instance_and_release_elastic_ip(instance)

        for volume in self.volumes:
            volume.delete()

    def spawn_ec2_instance(self):
        print "aws_region: " + aws_region
        print "time: " + str(datetime.datetime.now().time())

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

    def destroy_instance_and_release_elastic_ip(self, instance):
        instance.delete()
        self.servers.remove(instance)
        self._wait_for_instance_to_be_destroyed(instance.metadata['ec2_id'])
        self._wait_for_elastic_ip_to_be_released(instance.metadata['public_ip_address'])

    def _wait_for_elastic_ip_to_be_released(self, public_ip):
        while True:
            try:
                print 'Waiting for EC2 elastic ip to be released...'
                self.sleep_if_ec2_not_mocked(10)
                eip = self.ec2_conn.get_all_addresses(public_ip)
            except EC2ResponseError:
                print 'Elastic ip released.'
                break

    def _wait_for_instance_to_be_destroyed(self, ec2_id):
        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id])[0]
        # while ec2_instance.state not in ("shutting-down", "terminated"):
        while ec2_instance.state is not "terminated":
            print 'Waiting for EC2 instance to shut down...'
            self.sleep_if_ec2_not_mocked(10)
            ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id])[0]
        print 'Instance has been shut down.'