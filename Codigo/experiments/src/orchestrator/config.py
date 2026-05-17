"""Shared configuration for the SnapVM orchestrator experiments."""

HOST_IP = "172.16.0.1/24"
GUEST_IP = "172.16.0.2"
TAP_NAME = "vmtap0"

API_PORT = 3000
DB_PORT = 5432

WORKDIR = "workdir"
RESULTS_DIR = "results"
KERNEL_PATH = "images/vmlinux"
ROOTFS_PATH = "images/rootfs.ext4"
RUN_ROOTFS_PATH = "images/rootfs_run.ext4"

SNAPSHOT_DIR = "images/snapshots"
FIRECRACKER_SOCKET_PATH = "/tmp/firecracker.socket"
FIRECRACKER_PID_FILE = "/tmp/firecracker.pid"

DB_CONN = {
    "host": GUEST_IP,
    "port": DB_PORT,
    "user": "admin",
    "password": "admin",
    "dbname": "app_db",
}

HEALTH_URL = f"http://{GUEST_IP}:{API_PORT}/health"
EXEC_URL = f"http://{GUEST_IP}:{API_PORT}/exec"
