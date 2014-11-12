from collections import namedtuple
import unittest

from boto.ec2 import EC2Connection
from mock import Mock

from nova.virt.ec2.rule_comparator import RuleComparator
from fake_ec2_rule_builder import FakeEC2RuleBuilder


class TestRuleComparator(unittest.TestCase):

    def setUp(self):
        self.FakeSecurityGroup = namedtuple('FakeSecurityGroup', 'name')
        self.openstack_rule = {
            'ip_protocol': 'udp',
            'from_port': 1111,
            'to_port': 3333,
            'ip_range': {'cidr': '0.0.0.0/0'},
            'group': {}
        }

        self.ec2_connection = Mock(spec=EC2Connection)
        self.rule_comparator = RuleComparator(self.ec2_connection)

    def test_should_return_true_if_rules_have_matching_ip_protocol_from_port_to_port_and_ip_range(self):
        ec2_rule = FakeEC2RuleBuilder.an_ec2_rule()\
            .build()

        self.assertTrue(self.rule_comparator.rules_are_equal(self.openstack_rule, ec2_rule))

    def test_should_return_false_if_rules_have_different_ip_protocols(self):
        ec2_rule = FakeEC2RuleBuilder.an_ec2_rule()\
            .with_ip_protocol('tcp')\
            .build()

        self.assertFalse(self.rule_comparator.rules_are_equal(self.openstack_rule, ec2_rule))

    def test_should_return_false_if_rules_have_different_from_ports(self):
        ec2_rule = FakeEC2RuleBuilder.an_ec2_rule()\
            .with_from_port(2222)\
            .build()

        self.assertFalse(self.rule_comparator.rules_are_equal(self.openstack_rule, ec2_rule))

    def test_should_return_false_if_rules_have_different_to_ports(self):
        ec2_rule = FakeEC2RuleBuilder.an_ec2_rule()\
            .with_to_port(4444)\
            .build()

        self.assertFalse(self.rule_comparator.rules_are_equal(self.openstack_rule, ec2_rule))

    def test_should_return_false_if_rules_have_different_ip_range(self):
        ec2_rule = FakeEC2RuleBuilder.an_ec2_rule()\
            .with_ip_range('1.1.1.1/1')\
            .build()

        self.assertFalse(self.rule_comparator.rules_are_equal(self.openstack_rule, ec2_rule))

    def test_should_return_false_if_rules_have_allowed_groups_with_different_names(self):
        self.openstack_rule['ip_range'] = {}
        self.openstack_rule['group'] = {'name': 'secGroup'}

        self.ec2_connection.get_all_security_groups.return_value = [self.FakeSecurityGroup('secGroup2')]

        ec2_rule = FakeEC2RuleBuilder.an_ec2_rule()\
            .with_allowed_security_group_id(5)\
            .build()

        self.assertFalse(self.rule_comparator.rules_are_equal(self.openstack_rule, ec2_rule))

if __name__ == '__main__':
    unittest.main()