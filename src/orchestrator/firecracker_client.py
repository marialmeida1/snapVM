"""Firecracker API wrapper over UNIX socket."""

import os
import signal
import subprocess
import time

import requests_unixsocket

DEFAULT_SOCKET = "/tmp/firecracker.socket"
DEFAULT_PID_FILE = "/tmp/firecracker.pid"


class FirecrackerClient:
    def __init__(
        self,
        socket_path=DEFAULT_SOCKET,
        bin_path="bin/firecracker",
        pid_file=DEFAULT_PID_FILE,
    ):
        self.socket_path = socket_path
        self.bin_path = bin_path
        self.pid_file = pid_file
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
        if self._process and self._process.poll() is None:
            raise RuntimeError("Firecracker process is already running")
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
        self._process = subprocess.Popen(
            [self.bin_path, "--api-sock", self.socket_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait for socket to appear
        for _ in range(50):
            if self._process.poll() is not None:
                raise RuntimeError(
                    f"Firecracker exited before socket readiness (exit={self._process.returncode})"
                )
            if os.path.exists(self.socket_path):
                with open(self.pid_file, "w", encoding="utf-8") as f:
                    f.write(str(self._process.pid))
                return
            time.sleep(0.1)
        raise TimeoutError("Firecracker socket did not appear")

    def _wait_for_pid_exit(self, pid, timeout_s):
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.1)
        return False

    def _read_pid_file(self):
        if not os.path.exists(self.pid_file):
            return None
        with open(self.pid_file, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def _pid_matches_firecracker(self, pid):
        proc_cmdline = f"/proc/{pid}/cmdline"
        try:
            with open(proc_cmdline, "rb") as f:
                raw = f.read()
        except FileNotFoundError:
            return False
        args = [part.decode("utf-8", errors="ignore") for part in raw.split(b"\x00") if part]
        if not args:
            return False
        executable = os.path.basename(args[0])
        has_socket_arg = "--api-sock" in args and self.socket_path in args
        return "firecracker" in executable and has_socket_arg

    def kill(self):
        """Kill the firecracker process and clean up socket."""
        if self._process:
            if self._process.poll() is None:
                self._process.send_signal(signal.SIGTERM)
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=5)
            self._process = None
        else:
            pid = self._read_pid_file()
            if pid and self._pid_matches_firecracker(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                else:
                    if not self._wait_for_pid_exit(pid, timeout_s=5):
                        os.kill(pid, signal.SIGKILL)
                        self._wait_for_pid_exit(pid, timeout_s=5)
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)

    # -- VM configuration --

    def set_machine_config(self, vcpu_count=1, mem_size_mib=256, track_dirty_pages=False):
        return self._put("/machine-config", {
            "vcpu_count": vcpu_count,
            "mem_size_mib": mem_size_mib,
            "track_dirty_pages": track_dirty_pages,
        })

    def set_boot_source(
        self,
        kernel_path,
        boot_args="console=ttyS0 reboot=k panic=1 pci=off selinux=0 init=/sbin/init.sh",
    ):
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

    def create_snapshot(self, mem_path, snapshot_path, snapshot_type="Full"):
        return self._put("/snapshot/create", {
            "snapshot_type": snapshot_type,
            "snapshot_path": snapshot_path,
            "mem_file_path": mem_path,
        })

    def load_snapshot(self, mem_path, snapshot_path, enable_diff=False):
        return self._put("/snapshot/load", {
            "snapshot_path": snapshot_path,
            "mem_file_path": mem_path,
            "enable_diff_snapshots": enable_diff,
            "resume_vm": True,
        })
