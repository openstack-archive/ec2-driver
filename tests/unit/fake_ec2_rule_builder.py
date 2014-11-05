from collections import namedtuple

class FakeEC2RuleBuilder():

    EC2Rule = namedtuple('EC2Rule', 'ip_protocol from_port to_port grants parent')
    GroupOrCIDR = namedtuple('GroupOrCIDR', 'cidr_ip group_id')

    def __init__(self):
        self.ip_protocol = 'udp'
        self.from_port = '1111'
        self.to_port = '3333'
        self.ip_range = '0.0.0.0/0'
        self.allowed_security_group_id = None
        self.parent = None

    @staticmethod
    def an_ec2_rule():
        return FakeEC2RuleBuilder()

    def with_ip_protocol(self, ip_protocol):
        self.ip_protocol = ip_protocol
        return self

    def with_from_port(self, from_port):
        self.from_port = from_port
        return self

    def with_to_port(self, to_port):
        self.to_port = to_port
        return self

    def with_ip_range(self, ip_range):
        self.ip_range = ip_range
        self.allowed_security_group_id = None
        return self

    def with_allowed_security_group_id(self, allowed_security_group_id):
        self.allowed_security_group_id = allowed_security_group_id
        self.ip_range = None
        return self

    def build(self):
        grants = [self.GroupOrCIDR(self.ip_range, self.allowed_security_group_id)]
        return self.EC2Rule(self.ip_protocol, self.from_port, self.to_port, grants, self.parent)
