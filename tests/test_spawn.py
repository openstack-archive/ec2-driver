import unittest
import time

from novaclient.v1_1 import client
from ..credentials import get_nova_creds

from boto import ec2
from ..ec2driver_config import *


class TestSpawn(unittest.TestCase):

    def setUp(self):
        print "Establishing connection with AWS"
        self.ec2_conn = ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key_id,
                                              aws_secret_access_key=aws_secret_access_key)
        self.creds = get_nova_creds()

    # @unittest.skip("For fun")
    def test_spawn(self):
        print "Spawning an instance"
        nova = client.Client(**self.creds)
        image = nova.images.find(name="cirros-0.3.1-x86_64-uec")
        flavor = nova.flavors.find(name="m1.tiny")
        self.server = nova.servers.create(name="cirros-test", image=image.id, flavor=flavor.id)
        instance = nova.servers.get(self.server.id)
        while instance.status != 'ACTIVE':
            time.sleep(10)
            instance = nova.servers.get(self.server.id)

        instance = self.ec2_conn.get_only_instances(instance_ids=[self.server.metadata['ec2_id']], filters=None,
                                                    dry_run=False, max_results=None)

        self.assertTrue(len(instance) == 1)

    def tearDown(self):
        print "Cleanup: Destroying the instance used for testing"
        ec2_id = self.server.metadata['ec2_id']
        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False,
                                                        max_results=None)
        # EC2 statecode: 16->Running, 32->Shutting Down
        while ec2_instance[0].state_code != 16:
            time.sleep(10)
            ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False,
                                                            max_results=None)
            print ec2_instance[0].state, ec2_instance[0].state_code
        self.server.delete()

if __name__ == '__main__':
    unittest.main()