import unittest

from mock import Mock
from novaclient.v1_1.security_groups import SecurityGroupManager

from nova.virt.ec2.openstack_group_service import OpenstackGroupService


class TestOpenstackGroupService(unittest.TestCase):

    def setUp(self):
        self.security_group_manager = Mock(spec=SecurityGroupManager)
        self.openstack_group_service = OpenstackGroupService(self.security_group_manager)

    def test_should_get_group_from_nova_security_group_manager(self):
        security_group = Mock()
        security_group.name = 'secGroup'
        self.security_group_manager.list.return_value = [security_group]

        self.assertEqual(self.openstack_group_service.get_group(security_group.name), security_group)

    def test_should_get_group_from_nova_security_group_manager_when_multiple_groups_present(self):
        security_group1 = Mock()
        security_group1.name = 'secGroup'
        security_group2 = Mock()
        security_group2.name = 'otherGroup'
        self.security_group_manager.list.return_value = [security_group1, security_group2]

        self.assertEqual(self.openstack_group_service.get_group(security_group2.name), security_group2)