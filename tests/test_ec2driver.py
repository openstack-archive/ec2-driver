import unittest
import time

from novaclient.v1_1 import client
from ..credentials import get_nova_creds

from boto import ec2
from ..ec2driver_config import *


class EC2DriverTest(unittest.TestCase):

    def setUp(self):
        print "Establishing connection with AWS"
        self.ec2_conn = ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key_id,
                                              aws_secret_access_key=aws_secret_access_key)
        self.creds = get_nova_creds()
        self.server = None

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

        self.assertEqual(len(instance), 1)

    def test_destroy(self):
        print "Spawning an instance"
        nova = client.Client(**self.creds)
        image = nova.images.find(name="cirros-0.3.1-x86_64-uec")
        flavor = nova.flavors.find(name="m1.tiny")
        server = nova.servers.create(name="cirros-test", image=image.id, flavor=flavor.id)

        instance = nova.servers.get(server.id)
        while instance.status != 'ACTIVE':
            time.sleep(10)
            instance = nova.servers.get(server.id)

        instance = nova.servers.get(server.id)
        print instance.status
        ec2_id = instance.metadata['ec2_id']

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False,
                                                        max_results=None)
        # EC2 statecode: 16->Running, 32->Shutting Down
        while ec2_instance[0].state != "running":
            time.sleep(10)
            ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False,
                                                            max_results=None)
            print ec2_instance[0].state, ec2_instance[0].state_code

        instance.delete()

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False,
                                                        max_results=None)
        # EC2 statecode: 16->Running, 32->Shutting Down
        while ec2_instance[0].state != "shutting-down":
            time.sleep(10)
            ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False,
                                                            max_results=None)
            print ec2_instance[0].state, ec2_instance[0].state_code

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False,
                                                        max_results=None)

        self.assertEquals(ec2_instance[0].state, "shutting-down")

    def test_power_off(self):
        print "Spawning an instance"
        nova = client.Client(**self.creds)
        image = nova.images.find(name="cirros-0.3.1-x86_64-uec")
        flavor = nova.flavors.find(name="m1.tiny")
        self.server = nova.servers.create(name="cirros-test", image=image.id, flavor=flavor.id)
        instance = nova.servers.get(self.server.id)
        while instance.status != 'ACTIVE':
            time.sleep(10)
            instance = nova.servers.get(self.server.id)


        #Send poweroff to the instance
        nova.servers.stop(instance)

        while instance.status != 'SHUTOFF':
            time.sleep(5)
            instance = nova.servers.get(self.server.id)
            print "while: %s" % instance.status
        instance = nova.servers.get(self.server.id)
        print "Status after POWEROFF ing: %s" % instance.status

        #assert power off
        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[self.server.metadata['ec2_id']], filters=None,
                                                        dry_run=False, max_results=None)[0]
        self.assertEqual(ec2_instance.state, "stopped")

    def tearDown(self):
        if self.server is not None:
            print "Cleanup: Destroying the instance used for testing"
            self.server.delete()

if __name__ == '__main__':
    unittest.main()