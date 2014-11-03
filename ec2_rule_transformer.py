from copy import deepcopy
from rule import Rule


class EC2RuleTransformer:

    def __init__(self, ec2_connection):
        self.ec2_connection = ec2_connection

    def to_rule(self, ec2_rule):
        rule_args = deepcopy(ec2_rule)

        if ec2_rule.grants[0].cidr_ip:
            rule_args['ip_range'] = ec2_rule.grants[0].cidr_ip
        else:
            group_id = ec2_rule.grants[0].group_id
            rule_args['group_name'] = self.ec2_connection.get_all_security_groups(group_ids=group_id)[0]
        return Rule(**ec2_rule)