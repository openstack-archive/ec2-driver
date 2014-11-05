class OpenstackGroupService():

    def __init__(self, security_group_manager):
        self.security_group_manager = security_group_manager

    def get_group(self, group_name):
        return [group for group in self.security_group_manager.list() if group.name == group_name][0]