from time import sleep
import unittest
import urllib2
from boto.exception import EC2ResponseError

from novaclient.v1_1 import client
from ..ec2driver_config import *
from ec2_test_base import EC2TestBase

from random import randint

class TestSecurityGroups(EC2TestBase):

    def test_should_create_ec2_security_group_if_it_does_not_exist(self):
        instance, instance_id = self.spawn_ec2_instance()
        security_group = self.nova.security_groups.create("securityGroupName" + str(randint(1, 10000)), "Security group description")

        self.nova.servers.add_security_group(instance.id, security_group.name)

        matching_ec2_security_groups = self._wait_for_ec2_security_group_to_have_instance(security_group)
        self.assertEqual(len(matching_ec2_security_groups), 1)

    @unittest.skipIf(os.environ.get('MOCK_EC2'), 'Not supported by moto')
    def test_should_add_security_group_to_ec2_instance(self):
        instance, instance_id = self.spawn_ec2_instance()
        security_group = self.nova.security_groups.create("securityGroupName" + str(randint(1, 10000)), "Security group description")

        self.nova.servers.add_security_group(instance.id, security_group.name)

        matching_ec2_security_groups = self._wait_for_ec2_security_group_to_have_instance(security_group)
        self.assertEqual(instance.metadata['ec2_id'], matching_ec2_security_groups[0].instances()[0].id)

    @unittest.skipIf(os.environ.get('MOCK_EC2'), 'Not supported by moto')
    def test_should_remove_security_group_from_ec2_instance(self):
        # Setup
        instance, instance_id = self.spawn_ec2_instance()
        security_group = self.nova.security_groups.create("securityGroupName" + str(randint(1, 10000)), "Security group description")

        self.nova.servers.add_security_group(instance.id, security_group.name)

        matching_ec2_security_groups = self._wait_for_ec2_security_group_to_have_instance(security_group)

        self.assertEqual(matching_ec2_security_groups[0].instances()[0].id, instance.metadata['ec2_id'])

        # Action
        self.nova.servers.remove_security_group(instance.id, security_group.name)

        # Assertion
        updated_matching_ec2_security_group = self._wait_for_ec2_group_to_have_no_instances(security_group)

        self.assertEqual(updated_matching_ec2_security_group.instances(), [])

    def test_should_delete_security_group(self):
        pass

    def test_rules(self):
        pass

    def _wait_for_ec2_group_to_have_no_instances(self, security_group):
        updated_matching_ec2_security_group = self.ec2_conn.get_all_security_groups(groupnames=security_group.name)[0]
        while updated_matching_ec2_security_group.instances():
            updated_matching_ec2_security_group = self.ec2_conn.get_all_security_groups(groupnames=security_group.name)[
                0]
        return updated_matching_ec2_security_group

    def _wait_for_ec2_security_group_to_have_instance(self, security_group):
        matching_ec2_security_groups = self.ec2_conn.get_all_security_groups(groupnames=security_group.name)
        while not matching_ec2_security_groups:
            matching_ec2_security_groups = self.ec2_conn.get_all_security_groups(groupnames=security_group.name)
        return matching_ec2_security_groups

if __name__ == '__main__':
    unittest.main()
