# Firecracker Environment Replication Guide

This guide provides the exact commands to build the complete Firecracker microVM infrastructure for our baseline experiments from scratch. It assumes you are running on a bare-metal Linux machine with Docker installed and KVM enabled.

## Prerequisites Verification

Ensure hardware virtualization is enabled and accessible:
```bash
lsmod | grep kvm
```
*(You should see `kvm` and `kvm_intel` or `kvm_amd` in the output).*

Ensure you have access to KVM (you might need to add your user to the `kvm` group if not running as root):
```bash
[ -r /dev/kvm ] && [ -w /dev/kvm ] && echo "OK" || echo "Need KVM permissions"
```

## Step 1: Host Preparation (Installing Firecracker)

We need to download the official Firecracker binary and make it executable.

```bash
# Define target version
FC_VERSION="v1.7.0"
ARCH="$(uname -m)"

# Download Firecracker release archive
wget "https://github.com/firecracker-microvm/firecracker/releases/download/${FC_VERSION}/firecracker-${FC_VERSION}-${ARCH}.tgz"

# Extract and install binary
tar -xzvf firecracker-${FC_VERSION}-${ARCH}.tgz
sudo cp release-${FC_VERSION}-${ARCH}/firecracker-${FC_VERSION}-${ARCH} /usr/local/bin/firecracker
sudo chmod +x /usr/local/bin/firecracker

# Clean up
rm -rf firecracker-${FC_VERSION}-${ARCH}.tgz release-${FC_VERSION}-${ARCH}
firecracker --version
```

## Step 2: Kernel Acquisition (`vmlinux`)

Firecracker requires an uncompressed Linux kernel (`vmlinux`). While we can compile one from source, for our MVP we will use a pre-built minimal kernel provided by the Firecracker team (or an AWS sample kernel).

```bash
mkdir -p images
cd images

# Download a compatible uncompressed kernel
wget https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/${ARCH}/kernels/vmlinux.bin -O vmlinux
```

## Step 3: Rootfs Construction (`rootfs.ext4`)

We need a filesystem containing Node.js, PostgreSQL, and our application. We will use Docker to build the environment and then extract it into a raw `ext4` image.

### 3a. Create the Dockerfile

Create a file named `Dockerfile` in your project root:

```dockerfile
# Use a minimal base image
FROM debian:bookworm-slim

# Install system dependencies, PostgreSQL, and Node.js
RUN apt-get update && apt-get install -y \
    postgresql postgresql-contrib \
    curl \
    systemd \
    sysvinit-core \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configure PostgreSQL to accept connections
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER admin WITH SUPERUSER PASSWORD 'admin';" && \
    createdb -O admin app_db && \
    /etc/init.d/postgresql stop
RUN echo "host all all 0.0.0.0/0 md5" >> /etc/postgresql/15/main/pg_hba.conf
RUN echo "listen_addresses='*'" >> /etc/postgresql/15/main/postgresql.conf
USER root

# Create the working directory for our Node.js app
WORKDIR /opt/app
COPY src/ /opt/app/
# (Optional) RUN npm install

# Set up an init script (Firecracker requires an init process like systemd or a custom script)
COPY init.sh /sbin/init.sh
RUN chmod +x /sbin/init.sh

# Set the default entrypoint for the microVM
CMD ["/sbin/init.sh"]
```

### 3b. Create the Init Script (`init.sh`)

Firecracker boots the Linux kernel and expects `/sbin/init` (or similar) to take over. Create `init.sh`:

```bash
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
```

### 3c. Extract and Format to ext4

Build the Docker image and copy its filesystem out into an `ext4` disk image. This can be done without root using `mkfs.ext4`'s `-d` flag.

```bash
# 1. Build the Docker image
docker build -t firecracker-guest-image .

# 2. Create a temporary container
CONTAINER_ID=$(docker create firecracker-guest-image)

# 3. Export the filesystem
mkdir -p guest_rootfs
docker export $CONTAINER_ID | tar -xC guest_rootfs

# 4. Clean up container
docker rm $CONTAINER_ID

# 5. Create the raw ext4 image (size: 2GB)
# The -d flag populates the ext4 filesystem directly from the directory without mounting!
dd if=/dev/zero of=images/rootfs.ext4 bs=1M count=2048
mkfs.ext4 -d guest_rootfs images/rootfs.ext4

# 6. Clean up the extracted folder
rm -rf guest_rootfs
```

## Next: The Python Orchestrator

With `firecracker`, `vmlinux`, and `rootfs.ext4` in place, you can now write the Python control plane to interact with the Firecracker API (via UNIX socket) to boot the microVM, configure the TAP network interfaces, and eventually trigger the CoW snapshot functionality.
