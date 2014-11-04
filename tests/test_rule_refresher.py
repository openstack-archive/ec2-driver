import unittest

from boto.ec2 import EC2Connection
from mock import Mock
import novaclient
from novaclient.v1_1.servers import Server

from nova.virt.ec2.rule_refresher import RuleRefresher
from nova.virt.ec2.rule import Rule
from nova.virt.ec2.ec2_group_transformer import EC2GroupTransformer
from nova.virt.ec2.openstack_group_transformer import OpenstackGroupTransformer
from nova.virt.ec2.group import Group

GROUP_NAME = 'secGroup'
OTHER_GROUP_NAME = "otherSecGroup"

class TestRuleRefresher(unittest.TestCase):
    def setUp(self):
        self.new_openstack_rule = {'ip_protocol': 'abc', 'from_port': 1111, 'to_port': 2222, 'ip_range': {'cidr': '1.2.3.4/55'}}

        self.openstack_instance = Mock()
        self.openstack_instance.security_groups = [{'name': GROUP_NAME}]

        self.openstack_group = Mock()
        self.openstack_group.name = GROUP_NAME
        self.openstack_group_manager = Mock(spec=novaclient.v1_1.security_groups.SecurityGroupManager)
        self.openstack_group_manager.list.return_value = [self.openstack_group]

        self.ec2_group = Mock()
        self.ec2_group.name = GROUP_NAME
        self.ec2_connection = Mock(spec=EC2Connection)
        self.ec2_connection.get_all_security_groups.return_value = [self.ec2_group]

        self.openstack_group_transformer = Mock(spec=OpenstackGroupTransformer)
        self.ec2_group_transformer = Mock(spec=EC2GroupTransformer)

        self.rule_refresher = RuleRefresher(self.openstack_group_manager, self.ec2_connection,
                                            self.openstack_group_transformer, self.ec2_group_transformer)

    def test_should_add_rule_to_ec2_security_group_when_rule_associated_with_group_on_openstack(self):
        new_rule = Rule('hjkl', 7, 8, '9.9.9.9/99')
        transformed_openstack_group = Mock(spec=Group)
        transformed_openstack_group.rule_diff.return_value = [new_rule]
        self.openstack_group_transformer.to_group.return_value = transformed_openstack_group

        self.rule_refresher.refresh(self.openstack_instance)

        self.ec2_connection.authorize_security_group.assert_called_once_with(
            group_name=GROUP_NAME,
            ip_protocol=new_rule.ip_protocol,
            from_port=new_rule.from_port,
            to_port=new_rule.to_port,
            cidr_ip=new_rule.ip_range
        )

    def test_should_add_rule_to_corresponding_ec2_group_when_other_groups_present(self):
        openstack_group_with_new_rule = Mock()
        openstack_group_with_new_rule.name = OTHER_GROUP_NAME
        other_ec2_group = Mock()

        self.openstack_instance.security_groups = [{'name': GROUP_NAME}, {'name': OTHER_GROUP_NAME}]

        self.openstack_group_manager.list.return_value = [openstack_group_with_new_rule, self.openstack_group]

        def mock_get_all_security_groups(groupnames=None):
            if groupnames == other_ec2_group.name:
                return [other_ec2_group]
            return [self.ec2_group]
        self.ec2_connection.get_all_security_groups.side_effect = mock_get_all_security_groups

        new_rule = Rule('hjkl', 7, 8, '9.9.9.9/99')
        transformed_openstack_group = Mock(spec=Group)
        transformed_openstack_group.rule_diff.return_value = []
        transformed_openstack_group_with_new_rule = Mock(spec=Group)
        transformed_openstack_group_with_new_rule.rule_diff.return_value = [new_rule]

        def mock_openstack_to_group(openstack_group):
            if openstack_group == self.openstack_group:
                return transformed_openstack_group
            else:
                return transformed_openstack_group_with_new_rule
        self.openstack_group_transformer.to_group.side_effect = mock_openstack_to_group


        self.rule_refresher.refresh(self.openstack_instance)

        self.ec2_connection.authorize_security_group.assert_called_once_with(
            group_name=OTHER_GROUP_NAME,
            ip_protocol=new_rule.ip_protocol,
            from_port=new_rule.from_port,
            to_port=new_rule.to_port,
            cidr_ip=new_rule.ip_range
        )