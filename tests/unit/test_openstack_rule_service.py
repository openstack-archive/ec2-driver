import unittest

from mock import Mock, call
from novaclient.v1_1.security_groups import SecurityGroup

from nova.virt.ec2.openstack_rule_service import OpenstackRuleService
from nova.virt.ec2.openstack_group_service import OpenstackGroupService
from nova.virt.ec2.openstack_rule_transformer import OpenstackRuleTransformer


class TestOpenstackRuleService(unittest.TestCase):
    def setUp(self):
        self.security_group = Mock(spec=SecurityGroup)
        self.security_group.name = "secGroup"

        self.openstack_group_service = Mock(OpenstackGroupService)
        self.openstack_group_service.get_group.return_value = self.security_group
        self.openstack_rule_transformer = Mock(OpenstackRuleTransformer)

        self.openstack_rule_service = OpenstackRuleService(
            self.openstack_group_service,
            self.openstack_rule_transformer
        )

    def test_should_get_security_group_from_group_service(self):
        self.security_group.rules = []

        self.openstack_rule_service.get_rules_for_group(self.security_group.name)

        self.openstack_group_service.get_group.assert_called_once_with(self.security_group.name)

    def test_should_transform_rules_from_security_group(self):
        first_rule = Mock()
        second_rule = Mock()
        self.security_group.rules = [first_rule, second_rule]

        self.openstack_rule_service.get_rules_for_group(self.security_group.name)

        self.openstack_rule_transformer.to_rule.assert_has_calls([call(first_rule), call(second_rule)])

    def test_should_return_transformed_security_group_rules(self):
        first_rule = Mock()
        second_rule = Mock()
        self.security_group.rules = [first_rule, second_rule]

        first_transformed_rule = Mock()
        second_transformed_rule = Mock()
        self.openstack_rule_transformer.to_rule.side_effect = [first_transformed_rule, second_transformed_rule]

        actual_rules = self.openstack_rule_service.get_rules_for_group(self.security_group.name)

        self.assertEqual(actual_rules, set([first_transformed_rule, second_transformed_rule]))
