cd /opt/stack/keystone && /opt/stack/keystone/bin/keystone-all --config-file /etc/keystone/keystone.conf --debug &
cd /opt/stack/horizon && sudo tail -f /var/log/apache2/horizon_error.log &
cd /opt/stack/glance; /usr/local/bin/glance-registry --config-file=/etc/glance/glance-registry.conf &
cd /opt/stack/glance; /usr/local/bin/glance-api --config-file=/etc/glance/glance-api.conf &
cd /opt/stack/nova && /usr/local/bin/nova-api &
cd /opt/stack/nova && sg libvirtd '/usr/local/bin/nova-compute --config-file /etc/nova/nova.conf' &
cd /opt/stack/nova && /usr/local/bin/nova-conductor --config-file /etc/nova/nova.conf &
cd /opt/stack/nova && /usr/local/bin/nova-cert --config-file /etc/nova/nova.conf &
cd /opt/stack/nova && /usr/local/bin/nova-network --config-file /etc/nova/nova.conf &
cd /opt/stack/nova && /usr/local/bin/nova-scheduler --config-file /etc/nova/nova.conf &
cd /opt/stack/nova && /usr/local/bin/nova-novncproxy --config-file /etc/nova/nova.conf --web /opt/stack/noVNC
cd /opt/stack/nova && /usr/local/bin/nova-xvpvncproxy --config-file /etc/nova/nova.conf
cd /opt/stack/nova && /usr/local/bin/nova-consoleauth --config-file /etc/nova/nova.conf
cd /opt/stack/nova && /usr/local/bin/nova-objectstore --config-file /etc/nova/nova.conf &
cd /opt/stack/cinder && /opt/stack/cinder/bin/cinder-api --config-file /etc/cinder/cinder.conf &
cd /opt/stack/cinder && /opt/stack/cinder/bin/cinder-scheduler --config-file /etc/cinder/cinder.conf &
cd /opt/stack/cinder && /opt/stack/cinder/bin/cinder-volume --config-file /etc/cinder/cinder.conf &
cd /opt/stack/heat; bin/heat-engine --config-file=/etc/heat/heat.conf
cd /opt/stack/heat; bin/heat-api --config-file=/etc/heat/heat.conf
cd /opt/stack/heat; bin/heat-api-cfn --config-file=/etc/heat/heat.conf
cd /opt/stack/heat; bin/heat-api-cloudwatch --config-file=/etc/heat/heat.conf
