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
from collections import defaultdict

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
# Using defaultdict as we need to get a default EBS volume to be returned if we access this map with an unknown key
volume_map_no_default = {'ed6fcf64-8c74-49a0-a30c-76128c7bda47': 'vol-83db57cb',
			  'ac28d216-6dda-4a7b-86c4-d95209ae8181': 'vol-1eea8a56'}
volume_map = defaultdict(lambda: 'vol-83db57cb', volume_map_no_default)
keypair_map = {}

# The limit on maximum resources you could have in the AWS EC2.

VCPUS = 100
MEMORY_IN_MBS = 88192
DISK_IN_GB = 1028
