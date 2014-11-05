# ThoughtWorks OpenStack to EC2 Driver

Thank you for your interest in this project. This is a ThoughtWorks internal R&D project to make Hybrid cloud real!
So that enterprises can enjoy the benefits of the private cloud without being limited by it. 
In the event of all the Private cloud resources being utilised to their maximum capacity, the traffic can be managed 
by bursting to the public cloud for extra capacity. 

For now we are focusing on being able to burst to Amazon EC2.

This driver will provide the level of abstraction that is required for OpenStack Dashboard or APIs to use Amazon EC2 
as a hypervisor while continuing to be able to manage the existing private cloud. 

## Getting Started

- OpenStack Icehouse/Juno installed
- Python 2.7 and above
- Amazon Web Service (AWS) SDK for Python --  Boto 2.34

## Quick Setup Steps

1. `$ cd <openstack_root_dir>/nova/nova/virt/`
2. `$ git clone https://github.com/ThoughtWorksInc/OpenStack-EC2-Driver.git ec2`
3. `$ vim /etc/nova/nova.conf # make sure it contains the following options in the respective sections`

        [DEFAULT]
        compute_driver=ec2.EC2Driver

        [conductor]
        use_local=True

        [ec2driver]
        ec2_secret_access_key = <your_aws_secret_access_key>
        ec2_access_key_id = <your_aws_access_key_id>
4. `ec2driver_standard_config.py` can be edited to configure the default AMI, AWS region and endpoints. 
5. Restart the nova-compute service. You are now all set cloud burst!

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

\* In Amazon’s EC2 there is no concept of suspend and resume on instances. Therefore, we simply stop EC2 instances when suspended and start the instances when resumed, we do the same on pause and un-pause.