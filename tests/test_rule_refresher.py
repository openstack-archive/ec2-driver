import unittest

import boto

from boto.ec2 import EC2Connection
from mock import Mock
import novaclient
from novaclient.v1_1.servers import Server

from nova.virt.ec2.rule_refresher import RuleRefresher
from nova.virt.ec2.openstack_rule_transformer import OpenstackRuleTransformer
from nova.virt.ec2.ec2_rule_transformer import EC2RuleTransformer
from nova.virt.ec2.rule import Rule

GROUP_NAME = 'secGroup'

class TestRuleRefresher(unittest.TestCase):
    def setUp(self):
        self.existing_new_rule = {'ip_protocol': 'abc', 'from_port': 1111, 'to_port': 2222, 'ip_range': {'cidr': '1.2.3.4/55'}}

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

        self.openstack_rule_transformer = Mock(spec=OpenstackRuleTransformer)
        self.ec2_rule_transformer = Mock(spec=EC2RuleTransformer)

        self.rule_refresher = RuleRefresher(self.openstack_group_manager, self.ec2_connection,
                                            self.openstack_rule_transformer, self.ec2_rule_transformer)

    def test_should_add_rule_to_ec2_security_group_when_rule_associated_with_group_on_openstack(self):
        self.openstack_group.rules = [self.existing_new_rule]
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
        existing_openstack_rule = {'ip_protocol': 'hi', 'from_port': 3333, 'to_port': 4444, 'ip_range': {'cidr': '6.7.8.9/00'}}
        existing_ec2_rule = {'attribute': 'value'}
        existing_transformed_rule = Rule('sdfg', 5, 6, '7.7.7.7/77')
        new_transformed_rule = Rule('hjkl', 7, 8, '9.9.9.9/99')

        self.openstack_group.rules = [
            existing_openstack_rule,
            self.existing_new_rule
        ]
        self.ec2_group.rules = [existing_ec2_rule]

        def mock_openstack_to_rule(openstack_rule):
            return existing_transformed_rule if openstack_rule == existing_openstack_rule else new_transformed_rule

        def mock_ec2_to_rule(ec2_rule):
            if ec2_rule == existing_ec2_rule:
                return existing_transformed_rule

        self.openstack_rule_transformer.to_rule.side_effect = mock_openstack_to_rule
        self.ec2_rule_transformer.to_rule.side_effect = mock_ec2_to_rule

        self.rule_refresher.refresh(self.openstack_instance)

        self.ec2_connection.authorize_security_group.assert_called_once_with(
            group_name=GROUP_NAME,
            ip_protocol=self.existing_new_rule['ip_protocol'],
            from_port=self.existing_new_rule['from_port'],
            to_port=self.existing_new_rule['to_port'],
            cidr_ip=self.existing_new_rule['ip_range']['cidr']
        )

    def test_should_add_rule_to_corresponding_ec2_group_when_other_groups_present(self):
        openstack_group2 = Mock()
        openstack_group2.name = "group2"
        ec2_group2 = Mock()
        ec2_group2.rules = []
        self.ec2_group.rules = []

        self.openstack_group.rules = [self.existing_new_rule]
        openstack_group2.rules = []
        self.openstack_instance.security_groups = [{'name': GROUP_NAME}, {'name': openstack_group2.name}]

        self.openstack_group_manager.list.return_value = [openstack_group2, self.openstack_group]

        def mock_get_all_security_groups(groupnames=None):
            if groupnames == ec2_group2.name:
                return [ec2_group2]
            return [self.ec2_group]
        self.ec2_connection.get_all_security_groups.side_effect = mock_get_all_security_groups

        self.rule_refresher.refresh(self.openstack_instance)

        self.ec2_connection.authorize_security_group.assert_called_once_with(
            group_name=GROUP_NAME,
            ip_protocol=self.existing_new_rule['ip_protocol'],
            from_port=self.existing_new_rule['from_port'],
            to_port=self.existing_new_rule['to_port'],
            cidr_ip=self.existing_new_rule['ip_range']['cidr']
        )