import os

if os.environ.get('MOCK_EC2'):
    print "test environment"
    from ec2driver_test_config import *
else:
    print "prod env"
    from ec2driver_standard_config import *