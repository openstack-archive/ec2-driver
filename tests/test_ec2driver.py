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
        self.nova = client.Client(**self.creds)
        self.server = None

    def spawn_ec2_instance(self):
        print "Spawning an instance"
        image = self.nova.images.find(name="cirros-0.3.1-x86_64-uec")
        flavor = self.nova.flavors.find(name="m1.tiny")
        self.server = self.nova.servers.create(name="cirros-test", image=image.id, flavor=flavor.id)
        instance = self.nova.servers.get(self.server.id)
        while instance.status != 'ACTIVE':
            time.sleep(10)
            instance = self.nova.servers.get(self.server.id)
        return instance

    def test_spawn(self):
        self.spawn_ec2_instance()

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[self.server.metadata['ec2_id']], filters=None,
                                                    dry_run=False, max_results=None)

        self.assertEqual(ec2_instance[0].id, self.server.metadata['ec2_id'])

    def test_destroy(self):
        instance = self.spawn_ec2_instance()

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

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False,
                                                        max_results=None)

        self.assertEquals(ec2_instance[0].state, "shutting-down")

    def test_power_off(self):
        instance = self.spawn_ec2_instance()
        #Send poweroff to the instance
        self.nova.servers.stop(instance)

        while instance.status != 'SHUTOFF':
            time.sleep(5)
            instance = self.nova.servers.get(self.server.id)

        #assert power off
        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[self.server.metadata['ec2_id']], filters=None,
                                                        dry_run=False, max_results=None)[0]
        self.assertEqual(ec2_instance.state, "stopped")

    def test_soft_reboot(self):
        instance = self.spawn_ec2_instance()
        #Send reboot to the instance with reboot_type = 'soft'
        self.nova.servers.reboot(instance, client.servers.REBOOT_SOFT)

        # we are waiting for the status to actually get to 'Reboot' before beginning to wait for it to go to 'Active' status
        while instance.status != 'REBOOT':
            # We don't sleep here because the soft reboot may take less than a second
            instance = self.nova.servers.get(self.server.id)

        while instance.status != 'ACTIVE':
            time.sleep(5)
            instance = self.nova.servers.get(self.server.id)

        #assert restarted
        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[self.server.metadata['ec2_id']], filters=None,
                                                        dry_run=False, max_results=None)[0]
        self.assertEqual(ec2_instance.state, "running")

    def test_hard_reboot(self):
        instance = self.spawn_ec2_instance()
        #Send reboot to the instance with reboot_type = 'soft'
        self.nova.servers.reboot(instance, client.servers.REBOOT_HARD)

        # we are waiting for the status to actually get to 'Hard Reboot' before beginning to wait for it to go to 'Active' status
        while instance.status != 'HARD_REBOOT':
            time.sleep(5)
            instance = self.nova.servers.get(self.server.id)

        while instance.status != 'ACTIVE':
            time.sleep(5)
            instance = self.nova.servers.get(self.server.id)

        #assert restarted
        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[self.server.metadata['ec2_id']], filters=None,
                                                        dry_run=False, max_results=None)[0]
        self.assertEqual(ec2_instance.state, "running")

    def test_resize(self):
        instance = self.spawn_ec2_instance()

        new_flavor = self.nova.flavors.find(name="m1.small")

        # Resize instance with flavor = m1.small
        self.nova.servers.resize(instance, new_flavor)

        # wait for the status to actually go to Verify_Resize, before confirming the resize.
        while instance.status != 'VERIFY_RESIZE':
            time.sleep(5)
            instance = self.nova.servers.get(self.server.id)

        # Confirm the resize
        self.nova.servers.confirm_resize(instance)

        while instance.status != 'ACTIVE':
            time.sleep(5)
            instance = self.nova.servers.get(self.server.id)

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[self.server.metadata['ec2_id']], filters=None,
                                                        dry_run=False, max_results=None)[0]
        self.assertEqual(ec2_instance.instance_type, "t2.small")

    def tearDown(self):
        if self.server is not None:
            print "Cleanup: Destroying the instance used for testing"
            self.server.delete()

if __name__ == '__main__':
    unittest.main()