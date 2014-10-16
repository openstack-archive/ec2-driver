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

# This is the config file which is going to hold the values for being able
# to connect to the AWS Public cloud.


aws_region = "us-east-1"
aws_access_key_id = "AKIAIZJDDRNNJUWZ3LXA"
aws_secret_access_key = "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"

#Adding a Red Hat Linux image below
aws_ami = "ami-785bae10"
#aws_ami = "ami-864d84ee"
instance_type = "t2.micro"

# Mapping OpenStack's flavor IDs(which seems to be randomly assigned) to EC2's flavor names
flavor_map = {2: 't2.micro', 5: 't2.small', 1: 't2.medium', 3: 'c3.xlarge', 4: 'c3.2xlarge'}
#Add image maps key: image in openstack, Value: EC2_AMI_ID
image_map = {}
volume_map = {'3df37a34-662e-4aa8-b71d-b8313d2e945b': 'vol-83db57cb',
			  '7d63c661-7e93-445b-b3cb-765f1c8ae4c0': 'vol-1eea8a56'}
keypair_map = {}

# The limit on maximum resources you could have in the AWS EC2.

VCPUS = 100
MEMORY_IN_MBS = 88192
DISK_IN_GB = 1028
