from copy import deepcopy
from rule import Rule


class OpenstackRuleTransformer:
    def to_rule(self, openstack_rule):
        rule_args = {}
        rule_args['ip_protocol'] = openstack_rule['ip_protocol']
        rule_args['from_port'] = str(openstack_rule['from_port'])
        rule_args['to_port'] = str(openstack_rule['to_port'])

        if 'cidr' in openstack_rule['ip_range']:
            rule_args['ip_range'] = openstack_rule['ip_range']['cidr']
        else:
            rule_args['group_name'] = openstack_rule['group']['name']

        return Rule(**rule_args)
