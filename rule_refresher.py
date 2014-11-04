class RuleRefresher:

    def __init__(self, openstack_group_manager, ec2_conn, openstack_rule_transformer, ec2_rule_transformer):
        self.openstack_group_manager = openstack_group_manager
        self.ec2_conn = ec2_conn
        self.openstack_rule_transformer = openstack_rule_transformer
        self.ec2_rule_transformer = ec2_rule_transformer

    def refresh(self, openstack_instance):
        for group_dict in openstack_instance.security_groups:
            openstack_group = [group for group in self.openstack_group_manager.list() if group.name == group_dict['name']][0]
            ec2_group = self.ec2_conn.get_all_security_groups(groupnames=group_dict['name'])[0]

            for openstack_rule in openstack_group.rules:
                same_rule_exists_on_ec2 = False
                for ec2_rule in ec2_group.rules:
                    if self.openstack_rule_transformer.to_rule(openstack_rule) == self.ec2_rule_transformer.to_rule(ec2_rule):
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