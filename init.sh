#!/bin/bash
mount -t proc proc /proc
mount -t sysfs sys /sys
mount -t devtmpfs dev /dev

# Configure guest network interface
ip addr add 172.16.0.2/24 dev eth0
ip link set dev eth0 up
ip route add default via 172.16.0.1

# Start PostgreSQL
su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl start -D /etc/postgresql/15/main -l /var/log/postgresql/postgres.log -w"

# Start Node.js app
cd /opt/app
node server.js &

# Keep the VM alive
exec /bin/bash
