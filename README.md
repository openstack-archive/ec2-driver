# ThoughtWorks OpenStack to EC2 Driver

Thank you for your interest in this project. This is a ThoughtWorks internal R&D project to make Hybrid cloud real!
So that enterprises can enjoy the benefits of the private cloud without being limited by it. 
In the event of all the Private cloud resources being utilised to their maximum capacity, the traffic can be managed 
by bursting to the public cloud for extra capacity. 

For now we are focusing on being able to burst to Amazon EC2.

Whether you are using the 
OpenStack native Dashboard—Horizon
Or Command Line Interface (CLI) 
Or OpenStack APIs
Or Orchestrating using Heat
this Driver will provide the level of abstraction that is required to treat Amazon EC2 or any public cloud service provider as just another hypervisor with unlimited resources. 

## Getting Started

- OpenStack Icehouse/Juno installed
- Python 2.7 and above
- Amazon Web Service (AWS) SDK for Python --  Boto 2.34

## Quick Setup

1. `$ cd <openstack_root_dir>/nova/nova/virt/`
2. `$ git clone https://github.com/ThoughtWorksInc/OpenStack-EC2-Driver.git ec2`
3. `$ vim /etc/nova/nova.conf # add the following options in the respective sections`

        [DEFAULT]
        compute_driver=ec2.EC2Driver

        [conductor]
        use_local=True

        [ec2driver]
        ec2_secret_access_key = <your_aws_secret_access_key>
        ec2_access_key_id = <your_aws_access_key_id>
4. `ec2driver_standard_config.py` can be edited to configure the default AMI, AWS region and endpoints. 
5. Restart the nova-compute service. You are now all set cloud burst!
 
To see it in action, [watch this video](https://www.youtube.com/watch?v=DiMbp9go-To)

[![ScreenShot](https://github.com/stackforge/ec2-driver/blob/master/img/hybrid_cloud.png)](https://www.youtube.com/watch?v=DiMbp9go-To)

## Multi-node hybrid cloud
This will enable a hybrid cloud infrastucture using this driver on one of the multiple compute-hosts. Follow the Quick setup to install the EC2 Driver on a (psuedo) compute-host in it's own availability zone. 

1. `$ cd <openstack_root_dir>/nova/nova/virt/`
2. `$ cp ./cloud_burst_filter.py ../scheduler/filters/`
3. `$ vim /etc/nova/nova.conf # add the following options in the respective sections`

        [DEFAULT]
        cloud_burst = # Switch to enable could bursting
        cloud_burst_availability_zone = # The availability zone of only compute hosts with the public cloud driver

        scheduler_driver = nova.scheduler.filter_scheduler.FilterScheduler
        scheduler_available_filters = nova.scheduler.filters.all_filters
        scheduler_default_filters = RetryFilter, AvailabilityZoneFilter, RamFilter, ComputeFilter, ComputeCapabilitiesFilter, ImagePropertiesFilter, ServerGroupAntiAffinityFilter, ServerGroupAffinityFilter, CloudBurstFilter
4. Restart nova-api, nova-compute and nova-scheduler services for the filter to take effect.


### What's supported!
- Launch
- Reboot
- Terminate
- Resize
- Config drive / User Data
- Pause/Unpause*
- Suspend/Resume* 
- Attach/Detach/Swap Volume 
- Snapshot
- Security Groups
- Nova Diagnostics

###Some more to be added!

- Spice, VNC and RDP Console
- Serial Console Output
- iSCSI 
- Service Control


#For Contributors

###Instructions for Developer Environment setup
1. Install git, Virtualbox and Vagrant.
2. `$ git clone https://github.com/ThoughtWorksInc/OpenStack-EC2-Driver.git ec2`
3. `$ cd ec2/ && vagrant up` This will download the development environment from Vagrant clound and setup devstack. 
4. `$ vagrant ssh`
5. Edit nova.conf and add the ec2 configuration options, refer to step 3 in Quick setup guide.
6. Restart nova-compute
  - `~/devstack/rejoin-stack.sh`
  - go to the nova-cpu screen (`ctrl+a`, `7`)
  - restart the process with `ctrl+c`, press up, and then enter
  - go to nova-api (screen 6), and repeat
  
The driver should now be loaded. The contents of the repository is mapped to `/opt/stack/nova/nova/virt/ec2/`, and you can edit it directly from your host computer with an IDE of your choice.

###Running Tests
1. Moto can be used to mock the EC2 server. To install moto, run `sudo pip install moto`.
2. To optionally use Moto, run `source /opt/stack/nova/nova/virt/ec2/tests/setup_moto.sh`.
3. `~/devstack/rejoin-stack.sh`
4. `cd /opt/stack/nova/nova/virt/ec2/tests`
5. Use `nosetests -s test_ec2driver.py`
6. To stop Moto, run `source /opt/stack/nova/nova/virt/ec2/tests/shutdown_moto.sh`.

###Using tempest/tempest.conf to run tempest tests
1. Clone the tempest repo from https://github.com/openstack/tempest
2. `ln -s ~/nova/nova/virt/ec2/tempest/tempest.conf <path to tempest repo>/etc/tempest.conf`
3. `ln -s ~/nova/nova/virt/ec2/tempest/accounts.yaml <path to tempest repo>/etc/accounts.yaml`

\* In Amazon’s EC2 there is no concept of suspend and resume on instances. Therefore, we simply stop EC2 instances when suspended and start the instances when resumed, we do the same on pause and un-pause.

###License

    Copyright (c) 2014 ThoughtWorks
    All Rights Reserved.

    Licensed under the Apache License, Version 2.0 (the "License"); you may
    not use this file except in compliance with the License. You may obtain
    a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.
