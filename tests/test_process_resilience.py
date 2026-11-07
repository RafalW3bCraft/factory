"""Tests for process resilience, PID validation, and port boundaries."""

from __future__ import annotations

import os
import shutil
import subprocess
import unittest
import unittest.mock
from pathlib import Path
from tempfile import TemporaryDirectory

FACTORY_ROOT = Path(__file__).resolve().parent.parent


class ProcessResilienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for name in ("start-factory.sh", "stop-factory.sh"):
            shutil.copy2(FACTORY_ROOT / name, self.root / name)
        shutil.copytree(FACTORY_ROOT / "scripts", self.root / "scripts")
        (self.root / "src/factory").mkdir(parents=True)
        shutil.copy2(FACTORY_ROOT / "src/factory/process_identity.py", self.root / "src/factory/process_identity.py")
        self.env_patch = unittest.mock.patch.dict(
            os.environ, {"FACTORY_ALLOW_UNSAFE_HOST": "1", "FACTORY_PYTHON": shutil.which("python3") or "python3"}
        )
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temporary.cleanup()

    def test_stop_factory_corrupt_pid_files(self) -> None:
        """stop-factory.sh should safely ignore and remove corrupt or unsafe PID files."""
        stop_script = self.root / "stop-factory.sh"
        pids_dir = self.root / "logs" / "pids"
        pids_dir.mkdir(parents=True, exist_ok=True)

        corrupt_cases = {
            "foreman.pid": "not-a-number\n",
            "smith.pid": "-999\n",
            "inspector.pid": "1\n",  # PID 1 protection
            "stresser.pid": "0\n",
        }

        try:
            for fname, content in corrupt_cases.items():
                (pids_dir / fname).write_text(content, encoding="utf-8")

            res = subprocess.run(["bash", str(stop_script)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertIn("Invalid or unsafe PID", res.stdout)

            # Corrupt files should be cleaned up
            for fname in corrupt_cases:
                self.assertFalse((pids_dir / fname).exists(), f"{fname} should have been removed")
        finally:
            for fname in corrupt_cases:
                (pids_dir / fname).unlink(missing_ok=True)

    def test_start_factory_rejects_invalid_opencode_ports(self) -> None:
        """start-factory.sh must fail fast if OPENCODE_PORT is out-of-bounds or non-numeric."""
        start_script = self.root / "start-factory.sh"

        invalid_ports = ["80", "1023", "65536", "notanumber", "-1"]
        for port in invalid_ports:
            env = os.environ.copy()
            env["OPENCODE_PORT"] = port
            env["RESULT_REPO"] = "/abs/path"
            res = subprocess.run(["bash", str(start_script)], env=env, capture_output=True, text=True)
            self.assertEqual(res.returncode, 1, f"Port {port} should be rejected")
            self.assertIn("Invalid OPENCODE_PORT", res.stderr)

    def test_start_factory_concurrent_supervisor_detection(self) -> None:
        """start-factory.sh must abort if factory.pid contains a running PID."""
        start_script = self.root / "start-factory.sh"
        pids_dir = self.root / "logs" / "pids"
        pids_dir.mkdir(parents=True, exist_ok=True)
        factory_pid_file = pids_dir / "factory.pid"

        my_pid = str(os.getpid())
        factory_pid_file.write_text(f"{my_pid}\n", encoding="utf-8")

        try:
            env = os.environ.copy()
            env["RESULT_REPO"] = "/abs/path"
            res = subprocess.run(["bash", str(start_script)], env=env, capture_output=True, text=True)
            self.assertEqual(res.returncode, 1)
            self.assertIn("Process 'factory' is already running", res.stderr)
        finally:
            factory_pid_file.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
