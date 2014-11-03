class Rule:
    def __init__(self, ip_protocol, from_port, to_port, ip_range=None, group_name=None):
        self.ip_protocol = ip_protocol
        self.from_port = from_port
        self.to_port = to_port
        self.ip_range = ip_range
        self.group_name = group_name

    def __key(self):
        return self.ip_protocol, self.from_port, self.to_port, self.ip_range, self.group_name

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())