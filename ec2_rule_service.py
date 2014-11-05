class EC2RuleService:

    def __init__(self, ec2_connection, ec2_rule_transformer):
        self.ec2_connection = ec2_connection
        self.ec2_rule_transformer = ec2_rule_transformer

    def get_rules_for_group(self, group_name):
        group = self.ec2_connection.get_all_security_groups(groupnames=group_name)[0]
        return set([self.ec2_rule_transformer.to_rule(rule) for rule in group.rules])