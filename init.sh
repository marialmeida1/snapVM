#!/bin/bash
# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sys /sys
mount -t devtmpfs dev /dev

# Start PostgreSQL background daemon
su - postgres -c "/usr/lib/postgresql/15/bin/pg_ctl start -D /etc/postgresql/15/main -l /var/log/postgresql/postgres.log"

# Start the Node.js application
cd /opt/app
node server.js &

# Provide a shell for debugging (or wait indefinitely)
exec /bin/bash
