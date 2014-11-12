class InstanceRuleRefresher:

    def __init__(self, group_rule_refresher):
        self.group_rule_refresher = group_rule_refresher

    def refresh(self, instance):
        for group_name in self._get_group_names(instance):
            self.group_rule_refresher.refresh(group_name)

    def _get_group_names(self, instance):
        return [group['name'] for group in instance.security_groups]
