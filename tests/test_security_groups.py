from time import sleep
import unittest
import urllib2
from boto.exception import EC2ResponseError

from novaclient.v1_1 import client
from ..ec2driver_config import *
from ec2_test_base import EC2TestBase

from random import randint

class TestSecurityGroups(EC2TestBase):

    def setUp(self):
        EC2TestBase.setUp()

        self.instance, instance_id = self.spawn_ec2_instance()
        self.security_group = self.nova.security_groups.create("securityGroupName" + str(randint(1, 10000)),
                                                               "Security group description")
        self.nova.servers.add_security_group(self.instance.id, self.security_group.name)
        self.matching_ec2_security_groups = self._wait_for_ec2_security_group_to_have_instance(self.security_group)

    def test_should_create_ec2_security_group_if_it_does_not_exist(self):
        self.assertEqual(len(self.matching_ec2_security_groups), 1)

    @unittest.skipIf(os.environ.get('MOCK_EC2'), 'Not supported by moto')
    def test_should_add_security_group_to_ec2_instance(self):
        self.assertEqual(self.instance.metadata['ec2_id'], self.matching_ec2_security_groups[0].instances()[0].id)

    @unittest.skipIf(os.environ.get('MOCK_EC2'), 'Not supported by moto')
    def test_should_remove_security_group_from_ec2_instance(self):
        self.assertEqual(self.matching_ec2_security_groups[0].instances()[0].id, self.instance.metadata['ec2_id'])

        self.nova.servers.remove_security_group(self.instance.id, self.security_group.name)

        updated_matching_ec2_security_group = self._wait_for_ec2_group_to_have_no_instances(self.security_group)
        self.assertEqual(updated_matching_ec2_security_group.instances(), [])

    def test_should_add_rule_to_ec2_security_group_when_group_has_an_instance(self):
        pass

    def _wait_for_ec2_group_to_have_no_instances(self, security_group):
        updated_matching_ec2_security_group = self.ec2_conn.get_all_security_groups(groupnames=security_group.name)[0]
        while updated_matching_ec2_security_group.instances():
            updated_matching_ec2_security_group =\
                self.ec2_conn.get_all_security_groups(groupnames=security_group.name)[0]
        return updated_matching_ec2_security_group

    def _wait_for_ec2_security_group_to_have_instance(self, security_group):
        matching_ec2_security_groups = self.ec2_conn.get_all_security_groups(groupnames=security_group.name)
        while not matching_ec2_security_groups:
            matching_ec2_security_groups = self.ec2_conn.get_all_security_groups(groupnames=security_group.name)
        return matching_ec2_security_groups

if __name__ == '__main__':
    unittest.main()
