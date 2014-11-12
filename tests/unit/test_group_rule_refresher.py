import unittest

from boto.ec2 import EC2Connection
from mock import Mock

from nova.virt.ec2.group_rule_refresher import GroupRuleRefresher
from nova.virt.ec2.rule import Rule
from nova.virt.ec2.openstack_rule_service import OpenstackRuleService
from nova.virt.ec2.ec2_rule_service import EC2RuleService

GROUP_NAME = 'secGroup'
OTHER_GROUP_NAME = "otherSecGroup"

class TestGroupRuleRefresher(unittest.TestCase):
    def setUp(self):
        self.rule = Rule('hjkl', 7, 8, '9.9.9.9/99')
        self.openstack_instance = Mock()

        self.ec2_connection = Mock(EC2Connection)
        self.openstack_rule_service = Mock(OpenstackRuleService)
        self.ec2_rule_service = Mock(EC2RuleService)

        self.group_rule_refresher = GroupRuleRefresher(
            self.ec2_connection,
            self.openstack_rule_service,
            self.ec2_rule_service
        )

    def test_should_add_rule_to_ec2_security_group_when_rule_associated_with_group_on_openstack(self):
        self.openstack_rule_service.get_rules_for_group.return_value = set([self.rule])
        self.ec2_rule_service.get_rules_for_group.return_value = set()

        self.group_rule_refresher.refresh(GROUP_NAME)

        self.ec2_connection.authorize_security_group.assert_called_once_with(
            group_name=GROUP_NAME,
            ip_protocol=self.rule.ip_protocol,
            from_port=self.rule.from_port,
            to_port=self.rule.to_port,
            cidr_ip=self.rule.ip_range
        )

    def test_should_remove_rule_from_ec2_security_group_when_rule_not_associated_with_group_on_openstack(self):
        self.openstack_rule_service.get_rules_for_group.return_value = set()
        self.ec2_rule_service.get_rules_for_group.return_value = set([self.rule])

        self.group_rule_refresher.refresh(GROUP_NAME)

        self.ec2_connection.revoke_security_group.assert_called_once_with(
            group_name=GROUP_NAME,
            ip_protocol=self.rule.ip_protocol,
            from_port=self.rule.from_port,
            to_port=self.rule.to_port,
            cidr_ip=self.rule.ip_range
        )