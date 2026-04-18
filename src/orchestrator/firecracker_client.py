"""Firecracker API wrapper over UNIX socket."""

import os
import signal
import subprocess
import time

import requests_unixsocket

DEFAULT_SOCKET = "/tmp/firecracker.socket"


class FirecrackerClient:
    def __init__(self, socket_path=DEFAULT_SOCKET, bin_path="bin/firecracker"):
        self.socket_path = socket_path
        self.bin_path = bin_path
        self._process = None
        # requests-unixsocket expects http+unix://%2Ftmp%2Ffirecracker.socket/...
        encoded = socket_path.replace("/", "%2F")
        self._base = f"http+unix://{encoded}"
        self._session = requests_unixsocket.Session()

    def _put(self, path, body):
        r = self._session.put(f"{self._base}{path}", json=body)
        r.raise_for_status()
        return r

    def _patch(self, path, body):
        r = self._session.patch(f"{self._base}{path}", json=body)
        r.raise_for_status()
        return r

    def _get(self, path):
        r = self._session.get(f"{self._base}{path}")
        r.raise_for_status()
        return r

    # -- Daemon lifecycle --

    def spawn(self):
        """Start the firecracker process in the background."""
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        self._process = subprocess.Popen(
            [self.bin_path, "--api-sock", self.socket_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait for socket to appear
        for _ in range(50):
            if os.path.exists(self.socket_path):
                return
            time.sleep(0.1)
        raise TimeoutError("Firecracker socket did not appear")

    def kill(self):
        """Kill the firecracker process and clean up socket."""
        if self._process:
            try:
                self._process.send_signal(signal.SIGTERM)
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            self._process = None
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

    # -- VM configuration --

    def set_machine_config(self, vcpu_count=1, mem_size_mib=256):
        return self._put("/machine-config", {
            "vcpu_count": vcpu_count,
            "mem_size_mib": mem_size_mib,
        })

    def set_boot_source(self, kernel_path, boot_args="console=ttyS0 reboot=k panic=1 pci=off init=/sbin/init.sh"):
        return self._put("/boot-source", {
            "kernel_image_path": kernel_path,
            "boot_args": boot_args,
        })

    def set_rootfs(self, drive_path, drive_id="rootfs", read_only=False):
        return self._put(f"/drives/{drive_id}", {
            "drive_id": drive_id,
            "path_on_host": drive_path,
            "is_root_device": True,
            "is_read_only": read_only,
        })

    def set_network(self, iface_id="eth0", tap_name="vmtap0"):
        return self._put(f"/network-interfaces/{iface_id}", {
            "iface_id": iface_id,
            "host_dev_name": tap_name,
        })

    # -- Actions --

    def start(self):
        return self._put("/actions", {"action_type": "InstanceStart"})

    def pause(self):
        return self._patch("/vm", {"state": "Paused"})

    def resume(self):
        return self._patch("/vm", {"state": "Resumed"})

    # -- Snapshots --

    def create_snapshot(self, mem_path, snapshot_path):
        return self._put("/snapshot/create", {
            "snapshot_type": "Full",
            "snapshot_path": snapshot_path,
            "mem_file_path": mem_path,
        })

    def load_snapshot(self, mem_path, snapshot_path):
        return self._put("/snapshot/load", {
            "snapshot_path": snapshot_path,
            "mem_file_path": mem_path,
            "enable_diff_snapshots": False,
            "resume_vm": True,
        })
