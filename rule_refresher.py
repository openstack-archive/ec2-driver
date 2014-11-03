class RuleRefresher:

    def __init__(self, openstack_group_manager, ec2_conn, rule_comparator):
        self.openstack_group_manager = openstack_group_manager
        self.ec2_conn = ec2_conn
        self.rule_comparator = rule_comparator

    def refresh(self, openstack_instance):
        openstack_group = self.openstack_group_manager.list()[0]
        openstack_rules = openstack_group.rules

        ec2_group = self.ec2_conn.get_all_security_groups()[0]
        ec2_rules = ec2_group.rules

        for openstack_rule in openstack_rules:
            same_rule_exists_on_ec2 = False
            for ec2_rule in ec2_rules:
                if self.rule_comparator.rules_are_equal(openstack_rule, ec2_rule):
                    same_rule_exists_on_ec2 = True
                    break

            if not same_rule_exists_on_ec2:
                self.ec2_conn.authorize_security_group(
                    group_name=openstack_group.name,
                    ip_protocol=openstack_rule['ip_protocol'],
                    from_port=openstack_rule['from_port'],
                    to_port=openstack_rule['to_port'],
                    cidr_ip=openstack_rule['ip_range']['cidr']
                )


