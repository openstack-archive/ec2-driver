class OpenstackRuleService:
    def __init__(self, group_service, openstack_rule_transformer):
        self.group_service = group_service
        self.openstack_rule_transformer = openstack_rule_transformer

    def get_rules_for_group(self, group_name):
        openstack_group = self.group_service.get_group(group_name)
        return set([self.openstack_rule_transformer.to_rule(rule) for rule in openstack_group.rules])
        # return self.group_service.get_group(group_name).rules