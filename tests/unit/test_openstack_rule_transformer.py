import unittest

from nova.virt.ec2.openstack_rule_transformer import OpenstackRuleTransformer


class TestEC2RuleTransformer(unittest.TestCase):

    def setUp(self):
        self.openstack_rule_transformer = OpenstackRuleTransformer()

    def test_should_copy_to_port(self):
        openstack_rule = {
            'ip_protocol': 'abc',
            'from_port': 123,
            'to_port': 456,
            'group': {},
            'parent_group_id': 55,
            'ip_range': {'cidr': '9.8.7.6/55'},
            'id': 18
        }
        rule = self.openstack_rule_transformer.to_rule(openstack_rule)
        self.assertEqual(rule.to_port, openstack_rule['to_port'])