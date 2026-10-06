"""Tests for process resilience, PID validation, and port boundaries."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

FACTORY_ROOT = Path(__file__).resolve().parent.parent


class ProcessResilienceTests(unittest.TestCase):
    def test_stop_factory_corrupt_pid_files(self) -> None:
        """stop-factory.sh should safely ignore and remove corrupt or unsafe PID files."""
        stop_script = FACTORY_ROOT / "stop-factory.sh"
        pids_dir = FACTORY_ROOT / "logs" / "pids"
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
        start_script = FACTORY_ROOT / "start-factory.sh"

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
        start_script = FACTORY_ROOT / "start-factory.sh"
        pids_dir = FACTORY_ROOT / "logs" / "pids"
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
