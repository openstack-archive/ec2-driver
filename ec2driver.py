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
from threading import Lock
import base64
import time
from ec2driver_config import *
from boto import ec2
from boto import exception as boto_exc
from boto.exception import EC2ResponseError
from credentials import get_nova_creds

from boto.regioninfo import RegionInfo
from oslo.config import cfg
from novaclient.v1_1 import client
from ec2driver_config import *
from nova import block_device
from nova.compute import power_state
from nova.compute import task_states
from nova import db
from nova import exception
from nova.image import glance
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import loopingcall
from nova.virt import driver
from nova.virt import virtapi
from nova.compute import flavors
from novaclient.v1_1 import client
from credentials import get_nova_creds

LOG = logging.getLogger(__name__)

ec2driver_opts = [
    cfg.StrOpt('snapshot_image_format',
               help='Snapshot image format (valid options are : '
                    'raw, qcow2, vmdk, vdi). '
                    'Defaults to same as source image'),
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
CONF.register_opts(ec2driver_opts, 'ec2driver')

TIME_BETWEEN_API_CALL_RETRIES = 1.0

EC2_STATE_MAP = {
        "pending" : power_state.BUILDING,
        "running" : power_state.RUNNING,
        "shutting-down" : power_state.NOSTATE,
        "terminated" : power_state.SHUTDOWN,
        "stopping" :power_state.NOSTATE,
        "stopped" : power_state.SHUTDOWN
}

DIAGNOSTIC_KEYS_TO_FILTER = ['group', 'block_device_mapping']

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

class EC2Driver(driver.ComputeDriver):
    capabilities = {
        "has_imagecache": True,
        "supports_recreate": True,
    }

    """EC2 hypervisor driver. Respurposing for EC2"""

    def __init__(self, virtapi, read_only=False):
        super(EC2Driver, self).__init__(virtapi)
        self.host_status_base = {
            'vcpus': VCPUS,
            'memory_mb': MEMORY_IN_MBS,
            'local_gb': DISK_IN_GB,
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

        self.creds = get_nova_creds()
        self.nova = client.Client(**self.creds)

        region = RegionInfo(name=aws_region, endpoint=aws_endpoint)
        self.ec2_conn = ec2.EC2Connection(aws_access_key_id=aws_access_key_id,
                                         aws_secret_access_key=aws_secret_access_key,
                                         host=host,
                                         port=port,
                                         region=region,
                                         is_secure=secure)

        self.cloudwatch_conn = ec2.cloudwatch.connect_to_region(
            aws_region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

        self.security_group_lock = Lock()

        if not '_EC2_NODES' in globals():
            set_nodes([CONF.host])

    def init_host(self, host):
        """Initialize anything that is necessary for the driver to function,
        including catching up with currently running VM's on the given host.
        """
        return

    def list_instances(self):
        """Return the names of all the instances known to the virtualization
        layer, as a list.
        """
        all_instances = self.ec2_conn.get_all_instances()
        instance_ids = []
        for instance in all_instances:
            instance_ids.append(instance.id)
        return instance_ids

    def plug_vifs(self, instance, network_info):
        """Plug VIFs into networks."""
        pass

    def unplug_vifs(self, instance, network_info):
        """Unplug VIFs from networks."""
        pass

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        """Create a new instance/VM/domain on the virtualization platform.
        Once this successfully completes, the instance should be
        running (power_state.RUNNING).

        If this fails, any partial instance should be completely
        cleaned up, and the virtualization platform should be in the state
        that it was before this call began.

        :param context: security context <Not Yet Implemented>
        :param instance: nova.objects.instance.Instance
                         This function should use the data there to guide
                         the creation of the new instance.
        :param image_meta: image object returned by nova.image.glance that
                           defines the image from which to boot this instance
        :param injected_files: User files to inject into instance.
        :param admin_password: set in instance. <Not Yet Implemented>
        :param network_info:
           :py:meth:`~nova.network.manager.NetworkManager.get_instance_nw_info`
        :param block_device_info: Information about block devices to be
                                  attached to the instance.
        """
        LOG.info("***** Calling SPAWN *******************")
        LOG.info("****** %s" % instance._user_data)
        LOG.info("****** Allocating an elastic IP *********")
        elastic_ip_address = self.ec2_conn.allocate_address(domain='vpc')

        #Creating the EC2 instance
        flavor_type = flavor_map[instance.get_flavor().id]

        #passing user_data from the openstack instance which is Base64 encoded after decoding it.
        user_data = instance._user_data

        if user_data:
            user_data = base64.b64decode(user_data)

        reservation = self.ec2_conn.run_instances(aws_ami, instance_type=flavor_type, user_data=user_data)
        ec2_instance = reservation.instances

        ec2_id = ec2_instance[0].id
        self._wait_for_state(instance, ec2_id, "running", power_state.RUNNING)
        instance['metadata'].update({'ec2_id':ec2_id, 'public_ip_address':elastic_ip_address.public_ip})

        LOG.info("****** Associating the elastic IP to the instance *********")
        self.ec2_conn.associate_address(instance_id=ec2_id, allocation_id=elastic_ip_address.allocation_id)

    def snapshot(self, context, instance, image_id, update_task_state):
        """Snapshot an image of the specified instance
        on EC2 and create an Image which gets stored in AMI (internally in EBS Snapshot)
        :param context: security context
        :param instance: nova.objects.instance.Instance
        :param image_id: Reference to a pre-created image that will hold the snapshot.
        """
        LOG.info("***** Calling SNAPSHOT *******************")

        if instance['metadata']['ec2_id'] is None:
            raise exception.InstanceNotRunning(instance_id=instance['uuid'])

        # Adding the below line only alters the state of the instance and not
        # its image in OpenStack.
        update_task_state(
            task_state=task_states.IMAGE_UPLOADING, expected_state=task_states.IMAGE_SNAPSHOT)
        ec2_id = instance['metadata']['ec2_id']
        ec_instance_info = self.ec2_conn.get_only_instances(
            instance_ids=[ec2_id], filters=None, dry_run=False, max_results=None)
        ec2_instance = ec_instance_info[0]
        if ec2_instance.state == 'running':
            ec2_image_id = ec2_instance.create_image(name=str(
                image_id), description="Image from OpenStack", no_reboot=False, dry_run=False)
            LOG.info("Image has been created state to %s." % ec2_image_id)

        # The instance will be in pending state when it comes up, waiting forit to be in available
        self._wait_for_image_state(ec2_image_id, "available")

        image_api = glance.get_default_image_service()
        image_ref = glance.generate_image_url(image_id)

        metadata = {'is_public': False,
                    'location': image_ref,
                    'properties': {
                                   'kernel_id': instance['kernel_id'],
                                   'image_state': 'available',
                                   'owner_id': instance['project_id'],
                                   'ramdisk_id': instance['ramdisk_id'],
                                   'ec2_image_id': ec2_image_id
                    }
                    }

        image_api.update(context, image_id, metadata)

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):

        if reboot_type == 'SOFT':
            self._soft_reboot(
                context, instance, network_info, block_device_info)
        elif reboot_type == 'HARD':
            self._hard_reboot(
                context, instance, network_info, block_device_info)

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

    def finish_revert_migration(self, context, instance, network_info,
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
        self.ec2_conn.stop_instances(
            instance_ids=[ec2_id], force=False, dry_run=False)
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
        self.power_on(
            context=None, instance=instance, network_info=None, block_device_info=None)

    def suspend(self, instance):
        self.power_off(instance)

    def resume(self, context, instance, network_info, block_device_info=None):
        self.power_on(context, instance, network_info, block_device_info)

    def destroy(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True, migrate_data=None):
        LOG.info("***** Calling DESTROY *******************")
        if 'ec2_id' not in instance['metadata']:
            LOG.warning(_("Key '%s' not in EC2 instances") % instance['name'], instance=instance)
            return
        elif 'public_ip' not in instance['metadata'] and 'public_ip_address' not in instance['metadata']:
            print instance['metadata']
            LOG.warning(_("Public IP is null"), instance=instance)
            return
        else:
            # Deleting the instance from EC2
            ec2_id = instance['metadata']['ec2_id']
            try:
                ec2_instances = self.ec2_conn.get_only_instances(instance_ids=[ec2_id])
            except Exception:
                return
            if ec2_instances.__len__() == 0:
                LOG.warning(_("EC2 instance with ID %s not found") % ec2_id, instance=instance)
                return
            else:
                # get the elastic ip associated with the instance & disassociate
                # it, and release it
                elastic_ip_address = self.ec2_conn.get_all_addresses(addresses=instance['metadata']['public_ip_address'])[0]
                LOG.info("****** Disassociating the elastic IP *********")
                self.ec2_conn.disassociate_address(elastic_ip_address.public_ip)

                self.ec2_conn.stop_instances(instance_ids=[ec2_id], force=True)
                self.ec2_conn.terminate_instances(instance_ids=[ec2_id])
                self._wait_for_state(instance, ec2_id, "terminated", power_state.SHUTDOWN)
                LOG.info("****** Releasing the elastic IP ************")
                self.ec2_conn.release_address(allocation_id=elastic_ip_address.allocation_id)

    def attach_volume(self, context, connection_info, instance, mountpoint,
                      disk_bus=None, device_type=None, encryption=None):
        """Attach the disk to the instance at mountpoint using info."""
        instance_name = instance['name']
        if instance_name not in self._mounts:
            self._mounts[instance_name] = {}
        self._mounts[instance_name][mountpoint] = connection_info

        volume_id = connection_info['data']['volume_id']
        # ec2 only attaches volumes at /dev/sdf through /dev/sdp
        self.ec2_conn.attach_volume(volume_map[volume_id], instance['metadata']['ec2_id'], "/dev/sdn", dry_run=False)

    def detach_volume(self, connection_info, instance, mountpoint,
                      encryption=None):
        """Detach the disk attached to the instance."""
        try:
            del self._mounts[instance['name']][mountpoint]
        except KeyError:
            pass
        volume_id = connection_info['data']['volume_id']
        self.ec2_conn.detach_volume(volume_map[volume_id], instance_id=instance['metadata']['ec2_id'], device="/dev/sdn", force=False, dry_run=False)

    def swap_volume(self, old_connection_info, new_connection_info,
                    instance, mountpoint):
        """Replace the disk attached to the instance."""
        instance_name = instance['name']
        if instance_name not in self._mounts:
            self._mounts[instance_name] = {}
        self._mounts[instance_name][mountpoint] = new_connection_info

        old_volume_id = old_connection_info['data']['volume_id']
        new_volume_id = new_connection_info['data']['volume_id']

        self.detach_volume(old_connection_info, instance, mountpoint)
        # wait for the old volume to detach successfully to make sure /dev/sdn is available for the new volume to be attached
        time.sleep(60)
        self.ec2_conn.attach_volume(volume_map[new_volume_id], instance['metadata']['ec2_id'], "/dev/sdn", dry_run=False)
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
        LOG.info("*************** GET INFO ********************")
        if 'metadata' not in instance or 'ec2_id' not in instance['metadata']:
            raise exception.InstanceNotFound(instance_id=instance['name'])

        ec2_id = instance['metadata']['ec2_id']
        ec2_instances = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False, max_results=None)
        if ec2_instances.__len__() == 0:
            LOG.warning(_("EC2 instance with ID %s not found") % ec2_id, instance=instance)
            raise exception.InstanceNotFound(instance_id=instance['name'])
        ec2_instance = ec2_instances[0]
        return {'state': EC2_STATE_MAP.get(ec2_instance.state),
                'max_mem': 0,
                'mem': 0,
                'num_cpu': 2,
                'cpu_time': 0}

    def allow_key(self, key):
        for key_to_filter in DIAGNOSTIC_KEYS_TO_FILTER:
            if key == key_to_filter:
                return False
        return True

    def get_diagnostics(self, instance_name):
        LOG.info("******* GET DIAGNOSTICS *********************************************")
        instance = self.nova.servers.get(instance_name)

        ec2_id = instance.metadata['ec2_id']
        ec2_instances = self.ec2_conn.get_only_instances(instance_ids=[ec2_id], filters=None, dry_run=False, max_results=None)
        if ec2_instances.__len__() == 0:
            LOG.warning(_("EC2 instance with ID %s not found") % ec2_id, instance=instance)
            raise exception.InstanceNotFound(instance_id=instance['name'])
        ec2_instance = ec2_instances[0]

        diagnostics = {}
        for key, value in ec2_instance.__dict__.items() :
            if self.allow_key(key):
                diagnostics['instance.' + key] = str(value)


        metrics = self.cloudwatch_conn.list_metrics(dimensions={'InstanceId': ec2_id})
        import datetime
        for metric in metrics:
            end = datetime.datetime.utcnow()
            start = end - datetime.timedelta(hours=1)
            details = metric.query(start, end, 'Average', None, 3600)
            if (len(details) > 0):
                diagnostics['metrics.' + str(metric)] = details[0]

        return diagnostics

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

    def _get_ec2_instance_ids_with_security_group(self, ec2_security_group):
        return [instance.id for instance in ec2_security_group.instances()]

    def _get_openstack_instances_with_security_group(self, openstack_security_group):
        return [instance for instance in (self.nova.servers.list())
                if openstack_security_group.name in [group['name'] for group in instance.security_groups]]

    def _get_id_of_ec2_instance_to_update_security_group(self, ec2_instance_ids_for_security_group, ec2_ids_for_openstack_instances_for_security_group):
        return (set(ec2_ids_for_openstack_instances_for_security_group).symmetric_difference(set(ec2_instance_ids_for_security_group))).pop()

    def _should_add_security_group_to_instance(self, ec2_instance_ids_for_security_group, ec2_ids_for_openstack_instances_for_security_group):
        return len(ec2_instance_ids_for_security_group) < len(ec2_ids_for_openstack_instances_for_security_group)

    def _add_security_group_to_instance(self, ec2_instance_id, ec2_security_group):
        security_group_ids_for_instance = self._get_ec2_security_group_ids_for_instance(ec2_instance_id)
        security_group_ids_for_instance.append(ec2_security_group.id)
        self.ec2_conn.modify_instance_attribute(ec2_instance_id, "groupSet", security_group_ids_for_instance)

    def _remove_security_group_from_instance(self, ec2_instance_id, ec2_security_group):
        security_group_ids_for_instance = self._get_ec2_security_group_ids_for_instance(ec2_instance_id)
        security_group_ids_for_instance.remove(ec2_security_group.id)
        self.ec2_conn.modify_instance_attribute(ec2_instance_id, "groupSet", security_group_ids_for_instance)

    def _get_ec2_security_group_ids_for_instance(self, ec2_instance_id):
        security_groups_for_instance = self.ec2_conn.get_instance_attribute(ec2_instance_id, "groupSet")['groupSet']
        security_group_ids_for_instance = [group.id for group in security_groups_for_instance]
        return security_group_ids_for_instance

    def _get_or_create_ec2_security_group(self, openstack_security_group):
        try:
            return self.ec2_conn.get_all_security_groups(openstack_security_group.name)[0]
        except EC2ResponseError as e:
            LOG.warning(e.body)
            return self.ec2_conn.create_security_group(openstack_security_group.name, openstack_security_group.description)

    def refresh_security_group_rules(self, security_group_id):
        LOG.info("************** REFRESH SECURITY GROUP RULES ******************")

        openstack_security_group = self.nova.security_groups.get(security_group_id)
        ec2_security_group = self._get_or_create_ec2_security_group(openstack_security_group)

        ec2_ids_for_ec2_instances_with_security_group = self._get_ec2_instance_ids_with_security_group(ec2_security_group)
        ec2_ids_for_openstack_instances_with_security_group = [
            instance.metadata['ec2_id'] for instance
            in self._get_openstack_instances_with_security_group(openstack_security_group)
        ]

        self.security_group_lock.acquire()

        try:
            ec2_instance_to_update = self._get_id_of_ec2_instance_to_update_security_group(
                ec2_ids_for_ec2_instances_with_security_group,
                ec2_ids_for_openstack_instances_with_security_group
            )

            should_add_security_group = self._should_add_security_group_to_instance(
                ec2_ids_for_ec2_instances_with_security_group,
                ec2_ids_for_openstack_instances_with_security_group)

            if should_add_security_group:
                self._add_security_group_to_instance(ec2_instance_to_update, ec2_security_group)
            else:
                self._remove_security_group_from_instance(ec2_instance_to_update, ec2_security_group)
        finally:
            self.security_group_lock.release()

        return True

    def refresh_security_group_members(self, security_group_id):
        LOG.info("************** REFRESH SECURITY GROUP MEMBERS ******************")
        LOG.info(security_group_id)
        return True

    def refresh_instance_security_rules(self, instance):
        LOG.info("************** REFRESH INSTANCE SECURITY RULES ******************")
        LOG.info(instance)
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

        dic = {'vcpus': VCPUS,
               'memory_mb': MEMORY_IN_MBS,
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
        ec_instance_info = self.ec2_conn.get_only_instances(
            instance_ids=[ec2_id], filters=None, dry_run=False, max_results=None)
        ec2_instance = ec_instance_info[0]

        # EC2 instance needs to be stopped to modify it's attribute. So we stop the instance,
        # modify the instance type in this case, and then restart the instance.
        ec2_instance.stop()
        self._wait_for_state(instance, ec2_id, "stopped", power_state.SHUTDOWN)
        new_instance_type = flavor_map[migration['new_instance_type_id']]
        ec2_instance.modify_attribute('instanceType', new_instance_type)

    def confirm_migration(self, migration, instance, network_info):
        LOG.info("***** Calling CONFIRM MIGRATION *******************")
        ec2_id = instance['metadata']['ec2_id']
        ec_instance_info = self.ec2_conn.get_only_instances(
            instance_ids=[ec2_id], filters=None, dry_run=False, max_results=None)
        ec2_instance = ec_instance_info[0]
        ec2_instance.start()
        self._wait_for_state(instance, ec2_id, "running", power_state.RUNNING)

    def pre_live_migration(self, context, instance_ref, block_device_info,
                           network_info, disk, migrate_data=None):
        return

    def unfilter_instance(self, instance_ref, network_info):
        return

    def get_host_stats(self, refresh=False):
        """Return EC2 Host Status of name, ram, disk, network."""
        stats = []
        for nodename in _EC2_NODES:
            host_status = self.host_status_base.copy()
            host_status['hypervisor_hostname'] = nodename
            host_status['host_hostname'] = nodename
            host_status['host_name_label'] = nodename
            host_status['hypervisor_type'] = 'Amazon-EC2'
            host_status['vcpus'] = VCPUS
            host_status['memory_mb'] = MEMORY_IN_MBS
            host_status['local_gb'] = DISK_IN_GB
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

    def _wait_for_state(self, instance, ec2_id, desired_state, desired_power_state):
        def _wait_for_power_state():
            """Called at an interval until the VM is running again."""
            ec2_instance = self.ec2_conn.get_only_instances(instance_ids=[ec2_id])

            state = ec2_instance[0].state
            if state == desired_state:
                LOG.info("Instance has changed state to %s." % desired_state)
                raise loopingcall.LoopingCallDone()

        def _wait_for_status_check():
            ec2_instance = self.ec2_conn.get_all_instance_status(instance_ids=[ec2_id])[0]
            if ec2_instance.system_status.status == 'ok':
                LOG.info("Instance status check is %s / %s" %
                         (ec2_instance.system_status.status, ec2_instance.instance_status.status))
                raise loopingcall.LoopingCallDone()

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_power_state)
        timer.start(interval=1).wait()

        if desired_state == 'running':
            timer = loopingcall.FixedIntervalLoopingCall(_wait_for_status_check)
            timer.start(interval=0.5).wait()

    def _wait_for_image_state(self, ami_id, desired_state):
        # Timer to wait for the iamge to reach a state
        def _wait_for_state():
            """Called at an interval until the AMI image is available."""
            try:
                images = self.ec2_conn.get_all_images(image_ids=[ami_id], owners=None,
                                                      executable_by=None, filters=None, dry_run=None)
                state = images[0].state
                # LOG.info("\n\n\nImage id = %s" % ami_id + ", state = %s\n\n\n" % state)
                if state == desired_state:
                    LOG.info("Image has changed state to %s." % desired_state)
                    raise loopingcall.LoopingCallDone()
            except boto_exc.EC2ResponseError:
                pass

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_state)
        timer.start(interval=0.5).wait()



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
