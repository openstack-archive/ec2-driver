# ThoughtWorks OpenStack to EC2 Driver

Enjoy the benefits of the private cloud without being limited by it. 
Just like the present drivers let you leverage the various bankends like VMWare and Xen, this driver will let you use the public cloud to burst your cloud to. For now we are focusing on being able to burst to Amazon EC2.

Using the native OpenStack Dashboard or APIs you would be able to manage the EC2 cloud. 

## Getting Started

* OpenStack Icehouse
* Python 2.7 and above
* Amazon Web Service (AWS) SDK for Python --  Boto 2.31.1

##Dev Environment Setup

###Requirements
- Git
- VirtualBox
- Vagrant

###Instructions
1. Clone this repository: `git clone https://github.com/ThoughtWorksInc/OpenStack-EC2-Driver.git`
2. Run`vagrant up` from within the repository to create an Ubuntu virtualbox that will install devstack. This will take a couple minutes.
3. `vagrant ssh` to ssh into the new machine
4. Use `vim /etc/nova/nova.conf` to edit the nova configuration so that 
    - the compute_driver is set to ec2.EC2Driver
    - under the [conductor] section, add the following line
        use_local = True
5. Restart nova
  - `~/devstack/rejoin-stack.sh`
  - go to the nova-cpu screen (`ctrl+a`, `6`)
  - restart the process with `ctrl+c`, press up, and then enter
  - go to nova-api (screen 5), and repeat
  
The driver should now be loaded. The contents of the repository is mapped to `/opt/stack/nova/nova/virt/ec2/`, and you can edit it directly from your host computer with an IDE of your choice.

###Important notes
In Amazon’s EC2 there is no concept of suspend and resume on instances. Therefore, we simply stop EC2 instances when suspended and start the instances when resumed, we do the same on pause and un-pause.

##To Be Continued
