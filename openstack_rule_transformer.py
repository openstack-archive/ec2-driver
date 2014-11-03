from copy import deepcopy
from rule import Rule


class OpenStackRuleTransformer:

    def to_rule(self, openstack_rule):
        rule_args = deepcopy(openstack_rule)

        if 'cidr' in openstack_rule['ip_range']:
            rule_args['ip_range'] = openstack_rule['ip_range']['cidr']
        else:
            rule_args['group_name'] = openstack_rule['group']['name']

        return Rule(**openstack_rule)