import os
import signal
import subprocess
import tempfile
import unittest
from unittest import mock

from src.orchestrator import main, snapshot
from src.orchestrator.firecracker_client import FirecrackerClient


class SnapshotTests(unittest.TestCase):
    def test_capture_resumes_vm_when_snapshot_fails(self):
        class Client:
            def __init__(self):
                self.paused = False
                self.resumed = False

            def pause(self):
                self.paused = True

            def create_snapshot(self, **kwargs):
                raise RuntimeError("snapshot create failed")

            def resume(self):
                self.resumed = True

        client = Client()
        with self.assertRaises(RuntimeError):
            snapshot.capture(client)
        self.assertTrue(client.paused)
        self.assertTrue(client.resumed)

    def test_restore_requires_snapshot_artifacts(self):
        class Client:
            def kill(self):
                raise AssertionError("kill should not run without snapshot artifacts")

            def spawn(self):
                raise AssertionError("spawn should not run without snapshot artifacts")

        with tempfile.TemporaryDirectory() as tmp:
            mem = os.path.join(tmp, "memory.bin")
            vmstate = os.path.join(tmp, "vmstate")
            with mock.patch.object(snapshot, "MEM_FILE", mem), mock.patch.object(snapshot, "SNAPSHOT_FILE", vmstate):
                with self.assertRaises(FileNotFoundError):
                    snapshot.restore(Client())


class FirecrackerClientTests(unittest.TestCase):
    def test_kill_ignores_non_firecracker_pid_file_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            socket_path = os.path.join(tmp, "firecracker.socket")
            pid_file = os.path.join(tmp, "firecracker.pid")
            proc = subprocess.Popen(["sleep", "60"])
            try:
                with open(pid_file, "w", encoding="utf-8") as f:
                    f.write(str(proc.pid))
                open(socket_path, "w", encoding="utf-8").close()

                client = FirecrackerClient(socket_path=socket_path, pid_file=pid_file)
                client.kill()

                self.assertIsNone(proc.poll())
                self.assertFalse(os.path.exists(pid_file))
                self.assertFalse(os.path.exists(socket_path))
            finally:
                if proc.poll() is None:
                    os.kill(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)

    def test_kill_tolerates_corrupt_pid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            socket_path = os.path.join(tmp, "firecracker.socket")
            pid_file = os.path.join(tmp, "firecracker.pid")
            with open(pid_file, "w", encoding="utf-8") as f:
                f.write("invalid-pid")
            open(socket_path, "w", encoding="utf-8").close()

            client = FirecrackerClient(socket_path=socket_path, pid_file=pid_file)
            client.kill()

            self.assertFalse(os.path.exists(pid_file))
            self.assertFalse(os.path.exists(socket_path))

    def test_kill_terminates_tracked_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            socket_path = os.path.join(tmp, "firecracker.socket")
            pid_file = os.path.join(tmp, "firecracker.pid")
            proc = subprocess.Popen(["sleep", "60"])
            try:
                client = FirecrackerClient(socket_path=socket_path, pid_file=pid_file)
                client._process = proc
                client.kill()
                self.assertIsNotNone(proc.poll())
            finally:
                if proc.poll() is None:
                    os.kill(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)


class MainWorkflowTests(unittest.TestCase):
    def test_git_workdir_init_allows_repeated_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = os.path.join(tmp, "workdir")
            with mock.patch.object(main, "WORKDIR", workdir):
                main._git_init_workdir()
                main._git_commit_milestone()
                head_1 = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=workdir, text=True
                ).strip()
                self.assertTrue(head_1)

                main._git_init_workdir()
                main._git_commit_milestone()
                head_2 = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=workdir, text=True
                ).strip()
                self.assertTrue(head_2)

    def test_run_git_baseline_always_cleans_up_vm(self):
        class Client:
            def __init__(self):
                self.kill_calls = 0

            def kill(self):
                self.kill_calls += 1

        client = Client()
        with mock.patch.object(main, "_boot_vm", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                main.run_git_baseline(client)
        self.assertEqual(client.kill_calls, 1)

    def test_run_firecracker_baseline_always_cleans_up_vm(self):
        class Client:
            def __init__(self):
                self.kill_calls = 0

            def kill(self):
                self.kill_calls += 1

        client = Client()
        with mock.patch.object(main, "_boot_vm", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                main.run_firecracker_baseline(client)
        self.assertEqual(client.kill_calls, 1)


if __name__ == "__main__":
    unittest.main()
