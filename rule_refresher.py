class RuleRefresher:

    def __init__(self, ec2_conn, openstack_rule_service, ec2_rule_service):
        self.ec2_conn = ec2_conn
        self.openstack_rule_service = openstack_rule_service
        self.ec2_rule_service = ec2_rule_service

    def refresh(self, openstack_instance):
        for group_dict in openstack_instance.security_groups:
            # openstack_group = [group for group in self.openstack_group_manager.list() if group.name == group_dict['name']][0]
            # transformed_openstack_group = self.openstack_group_transformer.to_group(openstack_group)
            # ec2_group = self.ec2_conn.get_all_security_groups(groupnames=group_dict['name'])[0]
            # transformed_ec2_group = self.ec2_group_transformer.to_group(ec2_group)

            # TODO: transform openstack rules before finding difference
            openstack_rules = self.openstack_rule_service.get_rules_for_group(group_dict['name'])
            ec2_rules = self.ec2_rule_service.get_rules_for_group(group_dict['name'])

            for rule in openstack_rules - ec2_rules:
                self._create_rule_on_ec2(group_dict['name'], rule)

    def _create_rule_on_ec2(self, group_name, rule):
        self.ec2_conn.authorize_security_group(
            group_name=group_name,
            ip_protocol=rule.ip_protocol,
            from_port=rule.from_port,
            to_port=rule.to_port,
            cidr_ip=rule.ip_range
        )