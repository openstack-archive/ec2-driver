from copy import deepcopy
from rule import Rule


class OpenstackRuleTransformer:

    def to_rule(self, openstack_rule):
        rule_args = deepcopy(openstack_rule)

        self._delete_unused_rule_args(rule_args)

        if 'cidr' in openstack_rule['ip_range']:
            rule_args['ip_range'] = openstack_rule['ip_range']['cidr']
        else:
            rule_args['group_name'] = openstack_rule['group']['name']

        return Rule(**rule_args)

    def _delete_unused_rule_args(self, rule_args):
        del rule_args['group']
        del rule_args['parent_group_id']
        del rule_args['id']