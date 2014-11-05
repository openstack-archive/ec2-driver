from time import sleep
import unittest
from random import randint

from ...ec2driver_config import *
from ec2_test_base import EC2TestBase


class TestSecurityGroups(EC2TestBase):

    def setUp(self):
        EC2TestBase.setUp(self)

        self.instance, instance_id = self.spawn_ec2_instance()
        self.security_group = self.nova.security_groups.create("securityGroupName" + str(randint(1, 10000)),
                                                               "Security group description")
        self.nova.servers.add_security_group(self.instance.id, self.security_group.name)
        self.matching_ec2_security_groups = self._wait_for_ec2_security_group_to_have_instance(self.security_group)

    def tearDown(self):
        EC2TestBase.tearDown(self)
        self._destroy_security_group()

    def test_should_create_ec2_security_group_if_it_does_not_exist(self):
        self.assertEqual(len(self.matching_ec2_security_groups), 1)

    @unittest.skipIf(os.environ.get('MOCK_EC2'), 'Not supported by moto')
    def test_should_add_security_group_to_ec2_instance(self):
        self.assertEqual(self.matching_ec2_security_groups[0].instances()[0].id, self.instance.metadata['ec2_id'])

    @unittest.skipIf(os.environ.get('MOCK_EC2'), 'Not supported by moto')
    def test_should_remove_security_group_from_ec2_instance(self):
        self.assertEqual(self.matching_ec2_security_groups[0].instances()[0].id, self.instance.metadata['ec2_id'])

        self.nova.servers.remove_security_group(self.instance.id, self.security_group.name)

        updated_matching_ec2_security_group = self._wait_for_ec2_group_to_have_no_instances(self.security_group)
        self.assertEqual(updated_matching_ec2_security_group.instances(), [])
        
    @unittest.skipIf(os.environ.get('MOCK_EC2'), 'Not supported by moto')
    def test_should_add_rule_to_ec2_security_group_when_rule_is_added_to_openstack_group_associated_with_instance(self):
        security_group_rule = self.nova.security_group_rules.create(
            parent_group_id=self.security_group.id,
            ip_protocol='tcp',
            from_port='1234',
            to_port='4321',
            cidr='0.0.0.0/0'
        )

        ec2_security_group = self.ec2_conn.get_all_security_groups(groupnames=self.security_group.name)[0]
        ec2_rule = ec2_security_group.rules[0]

        self.assertEqual(ec2_rule.ip_protocol, security_group_rule['ip_protocol'])
        self.assertEqual(ec2_rule.from_port, security_group_rule['from_port'])
        self.assertEqual(ec2_rule.to_port, security_group_rule['to_port'])
        self.assertEqual(ec2_rule.grants[0].cidr_ip, security_group_rule['ip_range']['cidr'])

    def _destroy_security_group(self):
        print "Cleanup: Destroying security group"
        sleep(5)
        self.security_group.delete()
        self.ec2_conn.delete_security_group(self.security_group.name)

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
