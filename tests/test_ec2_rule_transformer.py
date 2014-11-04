from nova.virt.ec2.ec2_rule_transformer import EC2RuleTransformer
from mock import Mock
from fake_ec2_rule_builder import FakeEC2RuleBuilder

import unittest



class TestEC2RuleTransformer(unittest.TestCase):

    def setUp(self):
        self.ec2_connection = Mock()
        self.ec2_rule_transformer = EC2RuleTransformer(self.ec2_connection)

    def test_should_copy_ip_protocol_and_port_attributes(self):
        ec2_rule = FakeEC2RuleBuilder.an_ec2_rule().build()

        rule = self.ec2_rule_transformer.to_rule(ec2_rule)

        self.assertEqual(rule.ip_protocol, ec2_rule.ip_protocol)
        self.assertEqual(rule.from_port, ec2_rule.from_port)
        self.assertEqual(rule.to_port, ec2_rule.to_port)

    def test_should_copy_ip_range_attribute_from_grant(self):
        ec2_rule = FakeEC2RuleBuilder.an_ec2_rule().with_ip_range('5.6.7.8/90').build()

        rule = self.ec2_rule_transformer.to_rule(ec2_rule)

        self.assertEqual(rule.ip_range, ec2_rule.grants[0].cidr_ip)

    def test_should_set_group_name_from_grant(self):
        ec2_rule = FakeEC2RuleBuilder.an_ec2_rule().with_allowed_security_group_id(123).build()

        ec2_group = Mock()
        ec2_group.name = 'secGroup'
        self.ec2_connection.get_all_security_groups.return_value = [ec2_group]

        rule = self.ec2_rule_transformer.to_rule(ec2_rule)

        self.assertEqual(rule.group_name, 'secGroup')