import unittest
import time
import urllib2

from boto.regioninfo import RegionInfo
from novaclient.v1_1 import client
from boto import ec2

from ..credentials import get_nova_creds
from ..ec2driver_config import *


def sleep_if_ec2_not_mocked(seconds):
    if not os.environ.get('MOCK_EC2'):
        time.sleep(seconds)


class EC2DriverTest(unittest.TestCase):
    _multiprocess_shared_ = True

    @classmethod
    def setUp(self):
        print "Establishing connection with AWS"

        moto_region = RegionInfo(name=aws_region, endpoint=aws_endpoint)
        self.ec2_conn = ec2.EC2Connection(aws_access_key_id=aws_access_key_id,
                                         aws_secret_access_key=aws_secret_access_key,
                                         host=host,
                                         port=port,
                                         region = moto_region,
                                         is_secure=secure)

        self.creds = get_nova_creds()
        self.nova = client.Client(**self.creds)

        # nova client for cinder
        self.creds['service_type'] = 'volume'
        self.nova_volume = client.Client(**self.creds)
        self.servers = []
        self.volumes = []

    def spawn_ec2_instance(self):

        print "aws_region: " + aws_region

        print "Spawning an instance"
        image = self.nova.images.find(name="cirros-0.3.1-x86_64-uec")
        flavor = self.nova.flavors.find(name="m1.tiny")
        server = self.nova.servers.create(
            name="cirros-test", image=image.id, flavor=flavor.id)
        instance = self.nova.servers.get(server.id)
        while instance.status != 'ACTIVE':
            sleep_if_ec2_not_mocked(10)
            instance = self.nova.servers.get(server.id)
        self.servers.append(instance)
        return instance, server.id

    def test_spawn(self):
        print "******* Spawn Test ***********"
        instance, instance_ref = self.spawn_ec2_instance()

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[instance.metadata['ec2_id']])
        ec2_eip = self.ec2_conn.get_all_addresses(addresses=instance.metadata['public_ip_address'])[0]

        self.assertEqual(ec2_instance[0].id, instance.metadata['ec2_id'])
        self.assertEqual(ec2_eip.instance_id, instance.metadata['ec2_id'])


    def test_destroy(self):
        print "******* Destroy Test ***********"
        instance, instance_ref = self.spawn_ec2_instance()

        ec2_id = instance.metadata['ec2_id']

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id])[0]
        # EC2 statecode: 16->Running, 32->Shutting Down
        while ec2_instance.state != "running":
            sleep_if_ec2_not_mocked(10)
            ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id])[0]
        instance.delete()

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id])[0]
        # EC2 statecode: 16->Running, 32->Shutting Down
        while ec2_instance.state not in ("shutting-down", "terminated"):
            sleep_if_ec2_not_mocked(10)
            ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id])[0]

        self.assertTrue(ec2_instance.state in ("shutting-down", "terminated"))


    def test_power_off(self):
        print "******* Power Off Test ***********"
        instance, instance_ref = self.spawn_ec2_instance()
        # Send poweroff to the instance
        self.nova.servers.stop(instance)

        while instance.status != 'SHUTOFF':
            sleep_if_ec2_not_mocked(5)
            instance = self.nova.servers.get(instance.id)

        # assert power off
        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[instance.metadata['ec2_id']])[0]
        self.assertEqual(ec2_instance.state, "stopped")

    def test_soft_reboot(self):
        print "******* Soft Reboot Test ***********"
        instance, instance_ref = self.spawn_ec2_instance()
        # Send reboot to the instance with reboot_type = 'soft'
        self.nova.servers.reboot(instance, client.servers.REBOOT_SOFT)

        # we are waiting for the status to actually get to 'Reboot' before
        # beginning to wait for it to go to 'Active' status
        while instance.status != 'REBOOT':
            # We don't sleep here because the soft reboot may take less than a
            # second
            instance = self.nova.servers.get(instance.id)

        while instance.status != 'ACTIVE':
            sleep_if_ec2_not_mocked(5)
            instance = self.nova.servers.get(instance.id)

        #assert restarted
        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[instance.metadata['ec2_id']])[0]
        self.assertEqual(ec2_instance.state, "running")

    def test_hard_reboot(self):
        print "******* Hard Reboot Test ***********"
        instance, instance_ref = self.spawn_ec2_instance()
        # Send reboot to the instance with reboot_type = 'soft'
        self.nova.servers.reboot(instance, client.servers.REBOOT_HARD)

        # we are waiting for the status to actually get to 'Hard Reboot' before
        # beginning to wait for it to go to 'Active' status
        while instance.status != 'HARD_REBOOT':
            sleep_if_ec2_not_mocked(5)
            instance = self.nova.servers.get(instance.id)

        while instance.status != 'ACTIVE':
            sleep_if_ec2_not_mocked(5)
            instance = self.nova.servers.get(instance.id)

        #assert restarted
        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[instance.metadata['ec2_id']])[0]
        self.assertEqual(ec2_instance.state, "running")

    def test_resize(self):
        print "******* Resize Test ***********"
        instance, instance_ref = self.spawn_ec2_instance()

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[instance.metadata['ec2_id']])[0]

        ip_before_resize = self.ec2_conn.get_all_addresses(addresses=instance.metadata['public_ip_address'])[0]

        self.assertEqual(ec2_instance.instance_type, "t2.micro")

        new_flavor = self.nova.flavors.find(name="m1.small")

        # Resize instance with flavor = m1.small
        self.nova.servers.resize(instance, new_flavor)

        # wait for the status to actually go to Verify_Resize, before
        # confirming the resize.
        while instance.status != 'VERIFY_RESIZE':
            sleep_if_ec2_not_mocked(5)
            instance = self.nova.servers.get(instance.id)

        # Confirm the resize
        self.nova.servers.confirm_resize(instance)

        while instance.status != 'ACTIVE':
            sleep_if_ec2_not_mocked(5)
            instance = self.nova.servers.get(instance.id)

        ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[instance.metadata['ec2_id']])[0]
        # ip_after_resize = ec2_instance.ip_address
        ip_after_resize = self.ec2_conn.get_all_addresses(addresses=instance.metadata['public_ip_address'])[0]

        self.assertEqual(ec2_instance.instance_type, "t2.small")

        self.assertEqual(ip_before_resize.public_ip, ip_after_resize.public_ip)

    @unittest.skipIf(os.environ.get('TEST'), 'Not supported by moto')
    def test_user_data(self):
         """To test the spawn method by providing a file user_data for config drive.
         Will bring up a LAMP server.
         """
         content = open('user_data', 'r')
         user_data_content = content.read()
         image = self.nova.images.find(name="cirros-0.3.1-x86_64-uec")
         flavor = self.nova.flavors.find(name="m1.tiny")
         server = self.nova.servers.create(name="cirros-test", image=image.id, flavor=flavor.id,
                                           userdata=user_data_content)
         instance = self.nova.servers.get(server.id)
         while instance.status != 'ACTIVE' and 'ec2_id' not in instance.metadata:
             sleep_if_ec2_not_mocked(10)
             instance = self.nova.servers.get(server.id)
         self.servers.append(instance)

         ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[instance.metadata['ec2_id']], filters=None,
                                                         dry_run=False, max_results=None)
         print ec2_instance
         print ec2_instance[0].ip_address
         #getting the public ip of the ec2 instance
         url = "http://"+ec2_instance[0].ip_address+"/phpinfo.php"

         #wait for the instance to downalod all the dependencies for a LAMP server
         sleep_if_ec2_not_mocked(300)
         print url
         raw_response = urllib2.urlopen(url)
         print raw_response
         self.assertEqual(raw_response.code, 200)

    @unittest.skipIf(os.environ.get('TEST'), 'Not supported by moto')
    def test_diagnostics(self):
         print "******* Diagnostics Test ***********"
         instance, instance_ref = self.spawn_ec2_instance()
         print "instance_ref: ", instance_ref

         diagnostics = instance.diagnostics()[1]

         self.assertEqual(diagnostics['instance.instance_type'], 't2.micro')
         self.assertEqual(diagnostics['instance._state'], 'running(16)')

    def test_attach_volume(self):
        volume = self.nova_volume.volumes.create(1, snapshot_id=None, display_name='test', display_description=None, volume_type=None, availability_zone=None, imageRef=None)
        self.volumes.append(volume)
        instance, instance_ref = self.spawn_ec2_instance()
        self.nova.volumes.create_server_volume(instance_ref, volume.id, "/dev/sdb")
        time.sleep(30)
        volumes = self.nova.volumes.get_server_volumes(instance.id)
        self.assertIn(volume, volumes)

    @classmethod
    def tearDown(self):
        print "Cleanup: Destroying the instance used for testing"
        for instance in self.servers:
            instance.delete()
        # wait for all instances to completely shut down and detach volumes if any
        time.sleep(120)
        for volume in self.volumes:
            volume.delete()

if __name__ == '__main__':
    unittest.main()
