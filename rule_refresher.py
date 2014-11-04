class RuleRefresher:

    def __init__(self, openstack_group_manager, ec2_conn, openstack_group_transformer, ec2_group_transformer):
        self.openstack_group_manager = openstack_group_manager
        self.ec2_conn = ec2_conn
        self.openstack_group_transformer = openstack_group_transformer
        self.ec2_group_transformer = ec2_group_transformer

    def refresh(self, openstack_instance):
        for group_dict in openstack_instance.security_groups:
            openstack_group = [group for group in self.openstack_group_manager.list() if group.name == group_dict['name']][0]
            transformed_openstack_group = self.openstack_group_transformer.to_group(openstack_group)

            ec2_group = self.ec2_conn.get_all_security_groups(groupnames=group_dict['name'])[0]
            transformed_ec2_group = self.ec2_group_transformer.to_group(ec2_group)

            rules_in_openstack_group_not_in_ec2 = transformed_openstack_group.rule_diff(transformed_ec2_group)

            for rule in rules_in_openstack_group_not_in_ec2:
                self._create_rule_on_ec2(openstack_group, rule)

    def _create_rule_on_ec2(self, openstack_group, rule):
        self.ec2_conn.authorize_security_group(
            group_name=openstack_group.name,
            ip_protocol=rule.ip_protocol,
            from_port=rule.from_port,
            to_port=rule.to_port,
            cidr_ip=rule.ip_range
        )