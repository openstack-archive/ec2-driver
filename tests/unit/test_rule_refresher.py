import unittest

from boto.ec2 import EC2Connection
from mock import Mock

from nova.virt.ec2.rule_refresher import RuleRefresher
from nova.virt.ec2.rule import Rule
from nova.virt.ec2.openstack_rule_service import OpenstackRuleService
from nova.virt.ec2.ec2_rule_service import EC2RuleService

GROUP_NAME = 'secGroup'
OTHER_GROUP_NAME = "otherSecGroup"

class TestRuleRefresher(unittest.TestCase):
    def setUp(self):
        self.new_rule = Rule('hjkl', 7, 8, '9.9.9.9/99')
        self.openstack_instance = Mock()

        self.ec2_connection = Mock(EC2Connection)
        self.openstack_rule_service = Mock(OpenstackRuleService)
        self.ec2_rule_service = Mock(EC2RuleService)

        self.rule_refresher = RuleRefresher(
            self.ec2_connection,
            self.openstack_rule_service,
            self.ec2_rule_service
        )

    def test_should_add_rule_to_ec2_security_group_when_rule_associated_with_group_on_openstack(self):
        self.openstack_instance.security_groups = [{'name': GROUP_NAME}]

        self.openstack_rule_service.get_rules_for_group.return_value = set([self.new_rule])
        self.ec2_rule_service.get_rules_for_group.return_value = set()

        self.rule_refresher.refresh(self.openstack_instance)

        self.ec2_connection.authorize_security_group.assert_called_once_with(
            group_name=GROUP_NAME,
            ip_protocol=self.new_rule.ip_protocol,
            from_port=self.new_rule.from_port,
            to_port=self.new_rule.to_port,
            cidr_ip=self.new_rule.ip_range
        )

    def test_should_add_rule_to_corresponding_ec2_group_when_other_groups_present(self):
        self.openstack_instance.security_groups = [{'name': GROUP_NAME}, {'name': OTHER_GROUP_NAME}]

        def mock_get_rules_for_openstack_group(group_name):
            return set() if group_name == GROUP_NAME else set([self.new_rule])
        self.openstack_rule_service.get_rules_for_group.side_effect = mock_get_rules_for_openstack_group
        self.ec2_rule_service.get_rules_for_group.return_value = set()

        self.rule_refresher.refresh(self.openstack_instance)

        self.ec2_connection.authorize_security_group.assert_called_once_with(
            group_name=OTHER_GROUP_NAME,
            ip_protocol=self.new_rule.ip_protocol,
            from_port=self.new_rule.from_port,
            to_port=self.new_rule.to_port,
            cidr_ip=self.new_rule.ip_range
        )