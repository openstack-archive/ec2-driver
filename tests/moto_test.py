import os
import unittest
from boto import ec2
from boto.regioninfo import RegionInfo
from ..ec2driver_config import *

START_MOTO_SERVER_COMMAND = 'moto_server ec2 -p1234'
END_MOTO_SERVER_COMMAND = "ps aux | grep '%s' | grep -v grep | awk '{print $2}' | xargs kill -9"\
                          % START_MOTO_SERVER_COMMAND

class MotoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.system(START_MOTO_SERVER_COMMAND + "&")
        moto_region = RegionInfo(name='moto_region', endpoint="localhost:1234")
        cls.ec2_conn = ec2.EC2Connection(aws_access_key_id='the_key', aws_secret_access_key='the_secret',
                                          host='0.0.0.0', port='1234',
                                          region = moto_region,
                                          is_secure=False)
        print cls.ec2_conn

    def test_should_create_an_instance(self):
        reservation = self.ec2_conn.run_instances('ami-abcd1234')
        ec2_instances = reservation.instances
        self.assertEqual(len(ec2_instances), 1)

    @classmethod
    def tearDownClass(cls):
        os.system(END_MOTO_SERVER_COMMAND)

if __name__ == '__main__':
    unittest.main()


