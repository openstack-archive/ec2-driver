import unittest

from boto.ec2 import EC2Connection
from boto.ec2.securitygroup import SecurityGroup
from mock import Mock, call

from nova.virt.ec2.ec2_rule_service import EC2RuleService
from nova.virt.ec2.ec2_rule_transformer import EC2RuleTransformer
from nova.virt.ec2.tests.fake_ec2_rule_builder import FakeEC2RuleBuilder

class TestEC2RuleService(unittest.TestCase):

    def setUp(self):
        self.security_group = Mock(spec=SecurityGroup)
        self.security_group.name = "secGroup"

        self.ec2_connection = Mock(spec=EC2Connection)
        self.ec2_connection.get_all_security_groups.return_value = [self.security_group]
        self.ec2_rule_transformer = Mock(spec=EC2RuleTransformer)

        self.ec2_rule_service = EC2RuleService(self.ec2_connection, self.ec2_rule_transformer)

    def test_should_get_security_group_from_ec2_connection(self):
        self.security_group.rules = []

        self.ec2_rule_service.get_rules_for_group(self.security_group.name)

        self.ec2_connection.get_all_security_groups.assert_called_once_with(groupnames=self.security_group.name)

    def test_should_transform_rules_from_security_group(self):
        first_rule = Mock()
        second_rule = Mock()
        self.security_group.rules = [first_rule, second_rule]

        self.ec2_rule_service.get_rules_for_group(self.security_group.name)

        self.ec2_rule_transformer.to_rule.assert_has_calls([call(first_rule), call(second_rule)])

    def test_should_return_transformed_security_group_rules(self):
        first_rule = Mock()
        second_rule = Mock()
        self.security_group.rules = [first_rule, second_rule]

        first_transformed_rule = Mock()
        second_transformed_rule = Mock()
        self.ec2_rule_transformer.to_rule.side_effect = [first_transformed_rule, second_transformed_rule]

        actual_rules = self.ec2_rule_service.get_rules_for_group(self.security_group.name)

        self.assertEqual(actual_rules, set([first_transformed_rule, second_transformed_rule]))