import os

if os.environ.get('TEST'):
    print "test environment"
    from ec2driver_test_config import *
else:
    print "prod env"
    from ec2driver_standard_config import *