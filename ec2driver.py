# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright (c) 2014 Thoughtworks.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Connection to the Amazon Web Services - EC2 service"""

from nova.virt import driver

from boto import ec2
from ec2driver_config import *

from oslo.config import cfg

from nova import block_device
from nova.compute import power_state
from nova.compute import task_states
from nova import db
from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import loopingcall
from nova.virt import driver
from nova.virt import virtapi
from nova.compute import flavors

LOG = logging.getLogger(__name__)

ec2api_opts = [
    cfg.StrOpt('datastore_regex',
               help='Regex to match the name of a datastore.'),
    cfg.FloatOpt('task_poll_interval',
                 default=0.5,
                 help='The interval used for polling of remote tasks.'),
    cfg.IntOpt('api_retry_count',
               default=10,
               help='The number of times we retry on failures, e.g., '
                    'socket error, etc.'),
    cfg.IntOpt('vnc_port',
               default=5900,
               help='VNC starting port'),
    cfg.IntOpt('vnc_port_total',
               default=10000,
               help='Total number of VNC ports'),
    cfg.BoolOpt('use_linked_clone',
                default=True,
                help='Whether to use linked clone'),
    ]

CONF = cfg.CONF
CONF.register_opts(ec2api_opts, 'ec2driver')

TIME_BETWEEN_API_CALL_RETRIES = 1.0


def set_nodes(nodes):
    """Sets EC2Driver's node.list.

    It has effect on the following methods:
        get_available_nodes()
        get_available_resource
        get_host_stats()

    To restore the change, call restore_nodes()
    """
    global _EC2_NODES
    _EC2_NODES = nodes


def restore_nodes():
    """Resets EC2Driver's node list modified by set_nodes().

    Usually called from tearDown().
    """
    global _EC2_NODES
    _EC2_NODES = [CONF.host]


class EC2Instance(object):

    def __init__(self, name, state):
        self.name = name
        self.state = state

    def __getitem__(self, key):
        return getattr(self, key)


class EC2Driver(driver.ComputeDriver):
    capabilities = {
        "has_imagecache": True,
        "supports_recreate": True,
        }

    """EC2 hypervisor driver. Respurposing for EC2"""

    def __init__(self, virtapi, read_only=False):
        super(EC2Driver, self).__init__(virtapi)
        self.instances = {}
        self.host_status_base = {
          'vcpus': 100000,
          'memory_mb': 8000000000,
          'local_gb': 600000000000,
          'vcpus_used': 0,
          'memory_mb_used': 0,
          'local_gb_used': 100000000000,
          'hypervisor_type': 'EC2',
          'hypervisor_version': '1.0',
          'hypervisor_hostname': CONF.host,
          'cpu_info': {},
          'disk_available_least': 500000000000,
          }
        self._mounts = {}
        self._interfaces = {}

    #To connect to EC2
        self.ec2_conn = ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

        self.reservation = self.ec2_conn.get_all_reservations()

        if not '_EC2_NODES' in globals():
            set_nodes([CONF.host])

    def init_host(self, host):
        return

    def list_instances(self):
        return self.instances.keys()

    def plug_vifs(self, instance, network_info):
        """Plug VIFs into networks."""
        pass

    def unplug_vifs(self, instance, network_info):
        """Unplug VIFs from networks."""
        pass

    def _wait_for_state(self, instance, ec2_id, desired_state, desired_power_state):
        def _wait_for_power_state():
            """Called at an interval until the VM is running again."""
            ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id])
            state = ec2_instance[0].state

            if state == desired_state:
                LOG.info("Instance has changed state to %s." % desired_state)
                name = instance['name']
                ec2_instance = EC2Instance(name, desired_power_state)
                #TODO understand the need for the below line
                self.instances[name] = ec2_instance
                raise loopingcall.LoopingCallDone()

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_power_state)
        timer.start(interval=0.5).wait()

    def _wait_for_image_state(self, ami_id, desired_state):
        #Timer to wait for the iamge to reach a state
        def _wait_for_state():
            """Called at an interval until the AMI image is available."""
            images = self.ec2_conn.get_all_images(image_ids=[ami_id], owners=None,
                                                  executable_by=None, filters=None, dry_run=None)
            state = images[0].state

            if state == desired_state:
                LOG.info("Image has changed state to %s." % desired_state)
                raise loopingcall.LoopingCallDone()

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_state)
        timer.start(interval=0.5).wait()

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        LOG.info("***** Calling SPAWN *******************")
        #Creating the EC2 instance
        instance_type = flavor_map[instance.get_flavor().name]
        reservation = self.ec2_conn.run_instances(aws_ami, instance_type=instance_type)
        ec2_instance = reservation.instances
        instance['metadata'].update({'ec2_id':ec2_instance[0].id})

        ec2_id = ec2_instance[0].id
        self._wait_for_state(instance, ec2_id, "running", power_state.RUNNING)

    def snapshot(self, context, instance, name, update_task_state):
        LOG.info("***** Calling SNAPSHOT *******************")
        if instance['name'] not in self.instances:
            raise exception.InstanceNotRunning(instance_id=instance['uuid'])
        update_task_state(task_state=task_states.IMAGE_UPLOADING)

        ec2_id = instance['metadata']['ec2_id']
        ec_instance_info = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False, max_results=None)
        ec2_instance = ec_instance_info[0]
        if ec2_instance.state == 'running':
            image = ec2_instance.create_image(name=str(ec2_instance.id), description="Image from OpenStack", no_reboot=False, dry_run=False)
        LOG.info("Image has been created state to %s." % image)
        #The instance will be in pending state when it comes up, waiting for it to be in available
        self._wait_for_image_state(image, "available")
        #TODO we need to fix the queing issue in the images

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):

        if reboot_type == 'SOFT':
            self._soft_reboot(context, instance, network_info, block_device_info)
        elif reboot_type == 'HARD':
            self._hard_reboot(context, instance, network_info, block_device_info)

    def _soft_reboot(self, context, instance, network_info, block_device_info=None):
        LOG.info("***** Calling SOFT REBOOT *******************")
        ec2_id = instance['metadata']['ec2_id']
        self.ec2_conn.reboot_instances(instance_ids=[ec2_id], dry_run=False)
        LOG.info("Soft Reboot Complete.")

    def _hard_reboot(self, context, instance, network_info, block_device_info=None):
        LOG.info("***** Calling HARD REBOOT *******************")
        self.power_off(instance)
        self.power_on(context, instance, network_info, block_device)
        LOG.info("Hard Reboot Complete.")

    @staticmethod
    def get_host_ip_addr():
        return '192.168.0.1'

    def set_admin_password(self, instance, new_pass):
        pass

    def inject_file(self, instance, b64_path, b64_contents):
        pass

    def resume_state_on_host_boot(self, context, instance, network_info,
                                  block_device_info=None):
        pass

    def rescue(self, context, instance, network_info, image_meta,
               rescue_password):
        pass

    def unrescue(self, instance, network_info):
        pass

    def poll_rebooting_instances(self, timeout, instances):
        pass

    def migrate_disk_and_power_off(self, context, instance, dest,
                                   instance_type, network_info,
                                   block_device_info=None):
        pass

    def finish_revert_migration(self, instance, network_info,
                                block_device_info=None, power_on=True):
        pass

    def post_live_migration_at_destination(self, context, instance,
                                           network_info,
                                           block_migration=False,
                                           block_device_info=None):
        pass

    def power_off(self, instance):
        LOG.info("***** Calling POWER OFF *******************")
        # Powering off the EC2 instance
        ec2_id = instance['metadata']['ec2_id']
        self.ec2_conn.stop_instances(instance_ids=[ec2_id], force=False, dry_run=False)
        self._wait_for_state(instance, ec2_id, "stopped", power_state.SHUTDOWN)

    def power_on(self, context, instance, network_info, block_device_info):
        LOG.info("***** Calling POWER ON *******************")
        # Powering on the EC2 instance
        ec2_id = instance['metadata']['ec2_id']
        self.ec2_conn.start_instances(instance_ids=[ec2_id], dry_run=False)
        self._wait_for_state(instance, ec2_id, "running", power_state.RUNNING)

    def soft_delete(self, instance):
        pass

    def restore(self, instance):
        pass

    def pause(self, instance):
        self.power_off(instance)

    def unpause(self, instance):
        self.power_on(context=None, instance=instance, network_info=None, block_device_info=None)

    def suspend(self, instance):
        self.power_off(instance)

    def resume(self, context, instance, network_info, block_device_info=None):
        self.power_on(context, instance, network_info, block_device_info)

    def destroy(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True, migrate_data=None):
        name = instance['name']
        if name in self.instances:

            #Deleting the instance from EC2
            ec2_id = instance['metadata']['ec2_id']
            self.ec2_conn.stop_instances(instance_ids=[ec2_id], force=True)
            self.ec2_conn.terminate_instances(instance_ids=[ec2_id])
            self._wait_for_state(instance, ec2_id, "terminated", power_state.SHUTDOWN)

        else:
            LOG.warning(_("Key '%(key)s' not in instances '%(inst)s'") %
                        {'key': name,
                         'inst': self.instances}, instance=instance)

    def attach_volume(self, context, connection_info, instance, mountpoint,
                      encryption=None):
        """Attach the disk to the instance at mountpoint using info."""
        instance_name = instance['name']
        if instance_name not in self._mounts:
            self._mounts[instance_name] = {}
        self._mounts[instance_name][mountpoint] = connection_info
        return True

    def detach_volume(self, connection_info, instance, mountpoint,
                      encryption=None):
        """Detach the disk attached to the instance."""
        try:
            del self._mounts[instance['name']][mountpoint]
        except KeyError:
            pass
        return True

    def swap_volume(self, old_connection_info, new_connection_info,
                    instance, mountpoint):
        """Replace the disk attached to the instance."""
        instance_name = instance['name']
        if instance_name not in self._mounts:
            self._mounts[instance_name] = {}
        self._mounts[instance_name][mountpoint] = new_connection_info
        return True

    def attach_interface(self, instance, image_meta, vif):
        if vif['id'] in self._interfaces:
            raise exception.InterfaceAttachFailed('duplicate')
        self._interfaces[vif['id']] = vif

    def detach_interface(self, instance, vif):
        try:
            del self._interfaces[vif['id']]
        except KeyError:
            raise exception.InterfaceDetachFailed('not attached')

    def get_info(self, instance):
        if instance['name'] not in self.instances:
            raise exception.InstanceNotFound(instance_id=instance['name'])
        i = self.instances[instance['name']]
        return {'state': i.state,
                'max_mem': 0,
                'mem': 0,
                'num_cpu': 2,
                'cpu_time': 0}

    def get_diagnostics(self, instance_name):
        return {'cpu0_time': 17300000000,
                'memory': 524288,
                'vda_errors': -1,
                'vda_read': 262144,
                'vda_read_req': 112,
                'vda_write': 5778432,
                'vda_write_req': 488,
                'vnet1_rx': 2070139,
                'vnet1_rx_drop': 0,
                'vnet1_rx_errors': 0,
                'vnet1_rx_packets': 26701,
                'vnet1_tx': 140208,
                'vnet1_tx_drop': 0,
                'vnet1_tx_errors': 0,
                'vnet1_tx_packets': 662,
        }

    def get_all_bw_counters(self, instances):
        """Return bandwidth usage counters for each interface on each
           running VM.
        """
        bw = []
        return bw

    def get_all_volume_usage(self, context, compute_host_bdms):
        """Return usage info for volumes attached to vms on
           a given host.
        """
        volusage = []
        return volusage

    def block_stats(self, instance_name, disk_id):
        return [0L, 0L, 0L, 0L, None]

    def interface_stats(self, instance_name, iface_id):
        return [0L, 0L, 0L, 0L, 0L, 0L, 0L, 0L]

    def get_console_output(self, instance):
        return 'EC2 CONSOLE OUTPUT\nANOTHER\nLAST LINE'

    def get_vnc_console(self, instance):
        return {'internal_access_path': 'EC2',
                'host': 'EC2vncconsole.com',
                'port': 6969}

    def get_spice_console(self, instance):
        return {'internal_access_path': 'EC2',
                'host': 'EC2spiceconsole.com',
                'port': 6969,
                'tlsPort': 6970}

    def get_console_pool_info(self, console_type):
        return {'address': '127.0.0.1',
                'username': 'EC2user',
                'password': 'EC2password'}

    def refresh_security_group_rules(self, security_group_id):
        return True

    def refresh_security_group_members(self, security_group_id):
        return True

    def refresh_instance_security_rules(self, instance):
        return True

    def refresh_provider_fw_rules(self):
        pass

    def get_available_resource(self, nodename):
        """Updates compute manager resource info on ComputeNode table.

           Since we don't have a real hypervisor, pretend we have lots of
           disk and ram.
        """
        if nodename not in _EC2_NODES:
            return {}

        dic = {'vcpus': cpu_units,
               'memory_mb': memory_in_mbs,
               'local_gb': 1028,
               'vcpus_used': 0,
               'memory_mb_used': 0,
               'local_gb_used': 0,
               'hypervisor_type': 'EC2',
               'hypervisor_version': '1.0',
               'hypervisor_hostname': nodename,
               'disk_available_least': 0,
               'cpu_info': '?'}
        return dic

    def ensure_filtering_rules_for_instance(self, instance_ref, network_info):
        return

    def get_instance_disk_info(self, instance_name):
        return

    def live_migration(self, context, instance_ref, dest,
                       post_method, recover_method, block_migration=False,
                       migrate_data=None):
        post_method(context, instance_ref, dest, block_migration,
                            migrate_data)
        return

    def check_can_live_migrate_destination_cleanup(self, ctxt,
                                                   dest_check_data):
        return

    def check_can_live_migrate_destination(self, ctxt, instance_ref,
                                           src_compute_info, dst_compute_info,
                                           block_migration=False,
                                           disk_over_commit=False):
        return {}

    def check_can_live_migrate_source(self, ctxt, instance_ref,
                                      dest_check_data):
        return

    def finish_migration(self, context, migration, instance, disk_info,
                         network_info, image_meta, resize_instance,
                         block_device_info=None, power_on=True):
        LOG.info("***** Calling FINISH MIGRATION *******************")
        ec2_id = instance['metadata']['ec2_id']
        ec_instance_info = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False, max_results=None)
        ec2_instance = ec_instance_info[0]
        new_instance_type_name = flavors.get_flavor(migration['new_instance_type_id'])['name']

        # EC2 instance needs to be stopped to modify it's attribute. So we stop the instance,
        # modify the instance type in this case, and then restart the instance.
        ec2_instance.stop()
        self._wait_for_state(instance, ec2_id, "stopped", power_state.SHUTDOWN)
        new_instance_type = flavor_map[new_instance_type_name]
        ec2_instance.modify_attribute('instanceType', new_instance_type)

    def confirm_migration(self, migration, instance, network_info):
        LOG.info("***** Calling CONFIRM MIGRATION *******************")
        ec2_id = instance['metadata']['ec2_id']
        ec_instance_info = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False, max_results=None)
        ec2_instance = ec_instance_info[0]
        ec2_instance.start()
        self._wait_for_state(instance, ec2_id, "running", power_state.RUNNING)

    def pre_live_migration(self, context, instance_ref, block_device_info,
                           network_info, disk, migrate_data=None):
        return

    def unfilter_instance(self, instance_ref, network_info):
        return

    def test_remove_vm(self, instance_name):
        """Removes the named VM, as if it crashed. For testing."""
        self.instances.pop(instance_name)

    def get_host_stats(self, refresh=False):
        """Return EC2 Host Status of ram, disk, network."""
        stats = []
        for nodename in _EC2_NODES:
            host_status = self.host_status_base.copy()
            host_status['hypervisor_hostname'] = nodename
            host_status['host_hostname'] = nodename
            host_status['host_name_label'] = nodename
            stats.append(host_status)
        if len(stats) == 0:
            raise exception.NovaException("EC2Driver has no node")
        elif len(stats) == 1:
            return stats[0]
        else:
            return stats

    def host_power_action(self, host, action):
        """Reboots, shuts down or powers up the host."""
        return action

    def host_maintenance_mode(self, host, mode):
        """Start/Stop host maintenance window. On start, it triggers
        guest VMs evacuation.
        """
        if not mode:
            return 'off_maintenance'
        return 'on_maintenance'

    def set_host_enabled(self, host, enabled):
        """Sets the specified host's ability to accept new instances."""
        if enabled:
            return 'enabled'
        return 'disabled'

    def get_disk_available_least(self):
        pass

    def add_to_aggregate(self, context, aggregate, host, **kwargs):
        pass

    def remove_from_aggregate(self, context, aggregate, host, **kwargs):
        pass

    def get_volume_connector(self, instance):
        return {'ip': '127.0.0.1', 'initiator': 'EC2', 'host': 'EC2host'}

    def get_available_nodes(self, refresh=False):
        return _EC2_NODES

    def instance_on_disk(self, instance):
        return False

    def list_instance_uuids(self):
        return []


class EC2VirtAPI(virtapi.VirtAPI):
    def instance_update(self, context, instance_uuid, updates):
        return db.instance_update_and_get_original(context,
                                                   instance_uuid,
                                                   updates)

    def aggregate_get_by_host(self, context, host, key=None):
        return db.aggregate_get_by_host(context, host, key=key)

    def aggregate_metadata_add(self, context, aggregate, metadata,
                               set_delete=False):
        return db.aggregate_metadata_add(context, aggregate['id'], metadata,
                                         set_delete=set_delete)

    def aggregate_metadata_delete(self, context, aggregate, key):
        return db.aggregate_metadata_delete(context, aggregate['id'], key)

    def security_group_get_by_instance(self, context, instance):
        return db.security_group_get_by_instance(context, instance['uuid'])

    def security_group_rule_get_by_security_group(self, context,
                                                  security_group):
        return db.security_group_rule_get_by_security_group(
            context, security_group['id'])

    def provider_fw_rule_get_all(self, context):
        return db.provider_fw_rule_get_all(context)

    def agent_build_get_by_triple(self, context, hypervisor, os, architecture):
        return db.agent_build_get_by_triple(context,
                                            hypervisor, os, architecture)

    def instance_type_get(self, context, instance_type_id):
        return db.instance_type_get(context, instance_type_id)

    def block_device_mapping_get_all_by_instance(self, context, instance,
                                                 legacy=True):
        bdms = db.block_device_mapping_get_all_by_instance(context,
                                                           instance['uuid'])
        if legacy:
            bdms = block_device.legacy_mapping(bdms)
        return bdms

    def block_device_mapping_update(self, context, bdm_id, values):
        return db.block_device_mapping_update(context, bdm_id, values)
