import unittest
from mock import Mock, call
from nova.virt.ec2.group_rule_refresher import GroupRuleRefresher
from nova.virt.ec2.instance_rule_refresher import InstanceRuleRefresher


class TestInstanceRuleRefresher(unittest.TestCase):

    def test_should_call_group_rule_refresher_on_every_group_for_instance(self):

        group_rule_refresher = Mock(spec=GroupRuleRefresher)

        instance = Mock()
        first_group = {'name': 'firstGroup'}
        second_group = {'name': 'secondGroup'}
        instance.security_groups = [first_group, second_group]

        instance_rule_refresher = InstanceRuleRefresher(group_rule_refresher)
        instance_rule_refresher.refresh(instance)

        group_rule_refresher.refresh.assert_has_calls([call(first_group['name']), call(second_group['name'])])