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

1. Go to <OpenStack Root Dir>/nova/nova/virt/
2. `git clone https://github.com/ThoughtWorksInc/OpenStack-EC2-Driver.git ec2`
3. Go to /etc/nova/nova.conf and make sure it contains the following, you might have the default and conductor section already, but add the ec2driver section:-

        [DEFAULT]
        compute_driver=ec2.EC2Driver

        [conductor]
        use_local=True

        [ec2driver]
        ec2_secret_access_key = <your_aws_secret_access_key>
        ec2_access_key_id = <your_aws_access_key_id>
4. Now go to the ec2 directory that was cloned and edit the ec2driver_standard_config.py if required.
5. Restart the nova compute service. 

You are now all set cloud burst!

## What is supported!
Launch
Reboot
Terminate
Resize
Pause/Unpause*
Suspend/Resume*
Attach/Detach Volume
Snapshot

#For Contributors

###Instructions for Developer Environment setup
1. Install git, Virtualbox and Vagrant and Clone this repository: `git clone https://github.com/ThoughtWorksInc/OpenStack-EC2-Driver.git`
2. Run`vagrant up` from within the repository to create an Ubuntu virtualbox that will install devstack. This will take a couple minutes.
3. `vagrant ssh` to ssh into the new machine
4. Refer to Step 3 in Quick Setup to edit nova.conf
5. Restart nova
  - `~/devstack/rejoin-stack.sh`
  - go to the nova-cpu screen (`ctrl+a`, `7`)
  - restart the process with `ctrl+c`, press up, and then enter
  - go to nova-api (screen 6), and repeat
  
The driver should now be loaded. The contents of the repository is mapped to `/opt/stack/nova/nova/virt/ec2/`, and you can edit it directly from your host computer with an IDE of your choice.

###Running Tests
1. Moto can be used to mock the EC2 server. To install moto, run `pip install moto`.
1. To optionally use Moto, run `source /opt/stack/nova/nova/virt/ec2/tests/setup_moto.sh`.
2. `~/devstack/rejoin-stack.sh`
3. `cd /opt/stack/nova/nova/virt/ec2/tests`
4. Use `nosetests -s test_ec2driver.py`
5. To stop Moto, run `source /opt/stack/nova/nova/virt/ec2/tests/shutdown_moto.sh`.


* In Amazon’s EC2 there is no concept of suspend and resume on instances. Therefore, we simply stop EC2 instances when suspended and start the instances when resumed, we do the same on pause and un-pause.

