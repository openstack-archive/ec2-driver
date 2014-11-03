import unittest

import boto

from boto.ec2 import EC2Connection
from mock import Mock
import novaclient
from novaclient.v1_1.servers import Server

from nova.virt.ec2.rule_refresher import RuleRefresher
from nova.virt.ec2.rule_comparator import RuleComparator

GROUP_NAME = 'secGroup'

class TestRuleRefresher(unittest.TestCase):
    def setUp(self):
        self.new_rule = {'ip_protocol': 'abc', 'from_port': 1111, 'to_port': 2222, 'ip_range': {'cidr': '1.2.3.4/55'}}

        self.openstack_group = Mock()
        self.openstack_group.name = GROUP_NAME

        self.ec2_group = Mock()
        self.ec2_group.name = GROUP_NAME

        self.openstack_instance = Mock()
        self.openstack_instance.security_groups = [{'name': GROUP_NAME}]

        self.openstack_group_manager = Mock(spec=novaclient.v1_1.security_groups.SecurityGroupManager)
        self.openstack_group_manager.list.return_value = [self.openstack_group]

        self.ec2_connection = Mock(spec=EC2Connection)
        self.ec2_connection.get_all_security_groups.return_value = [self.ec2_group]

        self.rule_comparator = Mock(spec=RuleComparator)

        self.rule_refresher = RuleRefresher(self.openstack_group_manager, self.ec2_connection, self.rule_comparator)

    def test_should_add_rule_to_ec2_security_group_when_rule_associated_with_group_on_openstack(self):
        self.openstack_group.rules = [self.new_rule]
        self.ec2_group.rules = []

        self.rule_refresher.refresh(self.openstack_instance)

        self.ec2_connection.authorize_security_group.assert_called_once_with(
            group_name=GROUP_NAME,
            ip_protocol='abc',
            from_port=1111,
            to_port=2222,
            cidr_ip="1.2.3.4/55"
        )

    def test_should_add_rule_to_ec2_security_group_when_other_rule_already_on_both(self):
        existing_rule = {'ip_protocol': 'hi', 'from_port': 3333, 'to_port': 4444, 'ip_range': {'cidr': '6.7.8.9/00'}}
        existing_ec2_rule = {'attribute': 'value'}

        self.openstack_group.rules = [
            existing_rule,
            self.new_rule
        ]
        self.ec2_group.rules = [existing_ec2_rule]

        def mock_rules_are_equal(openstack_rule, ec2_rule):
            return openstack_rule == existing_rule
        self.rule_comparator.rules_are_equal.side_effect = mock_rules_are_equal

        self.rule_refresher.refresh(self.openstack_instance)

        self.ec2_connection.authorize_security_group.assert_called_once_with(
            group_name=GROUP_NAME,
            ip_protocol=self.new_rule['ip_protocol'],
            from_port=self.new_rule['from_port'],
            to_port=self.new_rule['to_port'],
            cidr_ip=self.new_rule['ip_range']['cidr']
        )