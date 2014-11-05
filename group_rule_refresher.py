class GroupRuleRefresher:

    def __init__(self, ec2_connection, openstack_rule_service, ec2_rule_service):
        self.ec2_conn = ec2_connection
        self.openstack_rule_service = openstack_rule_service
        self.ec2_rule_service = ec2_rule_service

    def refresh(self, group_name):
            openstack_rules = self.openstack_rule_service.get_rules_for_group(group_name)
            ec2_rules = self.ec2_rule_service.get_rules_for_group(group_name)

            for rule in openstack_rules - ec2_rules:
                self._create_rule_on_ec2(group_name, rule)

    def _create_rule_on_ec2(self, group_name, rule):
        self.ec2_conn.authorize_security_group(
            group_name=group_name,
            ip_protocol=rule.ip_protocol,
            from_port=rule.from_port,
            to_port=rule.to_port,
            cidr_ip=rule.ip_range
        )