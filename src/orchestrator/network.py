"""TAP network interface provisioning for host <-> guest communication."""

import subprocess

HOST_IP = "172.16.0.1/24"
GUEST_IP = "172.16.0.2"
TAP_NAME = "vmtap0"


def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def setup_tap(tap_name=TAP_NAME, host_ip=HOST_IP):
    """Create and configure a TAP interface."""
    teardown_tap(tap_name=tap_name)
    _run(["sudo", "ip", "tuntap", "add", "dev", tap_name, "mode", "tap"])
    _run(["sudo", "ip", "addr", "add", host_ip, "dev", tap_name])
    _run(["sudo", "ip", "link", "set", "dev", tap_name, "up"])


def teardown_tap(tap_name=TAP_NAME):
    """Destroy the TAP interface, ignoring errors if it doesn't exist."""
    try:
        _run(["sudo", "ip", "link", "del", tap_name])
    except subprocess.CalledProcessError:
        pass
