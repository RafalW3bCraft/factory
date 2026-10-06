"""Integration tests for factory shell scripts."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

FACTORY_ROOT = Path(__file__).resolve().parent.parent


class ShellScriptsIntegrationTests(unittest.TestCase):
    def test_bootstrap_repo_usage(self) -> None:
        cmd = ["bash", str(FACTORY_ROOT / "bootstrap-repo.sh"), "--help"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Usage: bootstrap-repo.sh", res.stdout)

    def test_bootstrap_repo_relative_path_rejected(self) -> None:
        cmd = ["bash", str(FACTORY_ROOT / "bootstrap-repo.sh"), "relative/path/workspace"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 1)
        self.assertIn("path must be absolute", res.stderr)

    def test_bootstrap_repo_creates_valid_git_repo(self) -> None:
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test_workspace"
            cmd = ["bash", str(FACTORY_ROOT / "bootstrap-repo.sh"), str(target)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertIn("Repository initialised", res.stdout)

            # Verify git repo and files
            self.assertTrue((target / ".git").is_dir())
            self.assertTrue((target / ".gitignore").is_file())
            self.assertTrue((target / "README.md").is_file())

            # Verify clean status
            status = subprocess.run(["git", "-C", str(target), "status", "--porcelain"], capture_output=True, text=True)
            self.assertEqual(status.stdout.strip(), "")

            # Verify running again fails (already a git repository)
            res_again = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res_again.returncode, 1)
            self.assertIn("already a git repository", res_again.stderr)

    def test_verify_milestone_script(self) -> None:
        script = FACTORY_ROOT / "scripts" / "verify-milestone.sh"
        # Usage check
        res_usage = subprocess.run(["bash", str(script), "--help"], capture_output=True, text=True)
        self.assertEqual(res_usage.returncode, 0)
        self.assertIn("Usage:", res_usage.stdout)

        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            repo.mkdir()
            subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Tester"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "tester@factory.invalid"], check=True)
            (repo / "file.txt").write_text("hello\n")
            subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "initial commit"], check=True)

            # Test clean revision pass
            res_clean = subprocess.run(["bash", str(script), str(repo), "HEAD"], capture_output=True, text=True)
            self.assertEqual(res_clean.returncode, 0)
            self.assertIn("Milestone verification PASSED", res_clean.stdout)

            # Test invalid revision fail
            res_bad_rev = subprocess.run(
                ["bash", str(script), str(repo), "nonexistent-branch-or-commit"], capture_output=True, text=True
            )
            self.assertEqual(res_bad_rev.returncode, 1)
            self.assertIn("Revision 'nonexistent-branch-or-commit' not found", res_bad_rev.stderr)

            # Test with passing command
            res_cmd_pass = subprocess.run(
                ["bash", str(script), str(repo), "HEAD", "true"], capture_output=True, text=True
            )
            self.assertEqual(res_cmd_pass.returncode, 0)

            # Test with failing command
            res_cmd_fail = subprocess.run(
                ["bash", str(script), str(repo), "HEAD", "false"], capture_output=True, text=True
            )
            self.assertEqual(res_cmd_fail.returncode, 1)
            self.assertIn("Verification command failed", res_cmd_fail.stderr)

            # Test dirty working tree failure
            (repo / "file.txt").write_text("modified content\n")
            res_dirty = subprocess.run(["bash", str(script), str(repo), "HEAD"], capture_output=True, text=True)
            self.assertEqual(res_dirty.returncode, 1)
            self.assertIn("Working tree is dirty", res_dirty.stderr)

    def test_load_env_shell_script(self) -> None:
        load_script = FACTORY_ROOT / "scripts" / "load_env.sh"
        with TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "TEST_KEY=safe_value\r\nQUOTED_KEY=\"with spaces\" # comment\r\nSINGLE_KEY='single_val' # cmt\r\n",
                encoding="utf-8",
            )

            bash_cmd = f"""
            source {load_script}
            load_env_safe {env_file}
            echo "KEY1=$TEST_KEY"
            echo "KEY2=$QUOTED_KEY"
            echo "KEY3=$SINGLE_KEY"
            """
            res = subprocess.run(["bash", "-c", bash_cmd], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            self.assertIn("KEY1=safe_value", res.stdout)
            self.assertIn("KEY2=with spaces", res.stdout)
            self.assertIn("KEY3=single_val", res.stdout)

    def test_stop_factory_when_not_running(self) -> None:
        stop_script = FACTORY_ROOT / "stop-factory.sh"
        res = subprocess.run(["bash", str(stop_script)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Factory shutdown complete", res.stdout)


if __name__ == "__main__":
    unittest.main()
