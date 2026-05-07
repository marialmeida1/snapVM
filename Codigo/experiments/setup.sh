#!/bin/bash
set -e

echo "Starting Environment Setup..."

mkdir -p bin images src

echo "=== Step 1: Downloading Firecracker ==="
FC_VERSION="v1.7.0"
ARCH="$(uname -m)"

if [ ! -f "bin/firecracker" ]; then
    wget -q "https://github.com/firecracker-microvm/firecracker/releases/download/${FC_VERSION}/firecracker-${FC_VERSION}-${ARCH}.tgz"
    tar -xzvf firecracker-${FC_VERSION}-${ARCH}.tgz
    mv release-${FC_VERSION}-${ARCH}/firecracker-${FC_VERSION}-${ARCH} bin/firecracker
    chmod +x bin/firecracker
    rm -rf firecracker-${FC_VERSION}-${ARCH}.tgz release-${FC_VERSION}-${ARCH}
fi
echo "Firecracker version: $(./bin/firecracker --version | head -n 1)"

echo "=== Step 2: Downloading Kernel (vmlinux) ==="
if [ ! -f "images/vmlinux" ]; then
    wget -q https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/${ARCH}/kernels/vmlinux.bin -O images/vmlinux
fi

echo "=== Step 3: Building Rootfs (rootfs.ext4) ==="
if [ ! -f "images/rootfs.ext4" ]; then
    echo "Building Docker image..."
    docker build -t firecracker-guest-image .
    
    echo "Exporting filesystem..."
    CONTAINER_ID=$(docker create firecracker-guest-image)
    mkdir -p guest_rootfs
    docker export $CONTAINER_ID | tar -xC guest_rootfs
    docker rm $CONTAINER_ID
    
    echo "Creating ext4 image..."
    dd if=/dev/zero of=images/rootfs.ext4 bs=1M count=1024
    mkfs.ext4 -d guest_rootfs images/rootfs.ext4
    
    echo "Cleaning up..."
    rm -rf guest_rootfs
fi

echo "Setup Complete! Firecracker binary is in ./bin/, Kernel and Rootfs are in ./images/"
