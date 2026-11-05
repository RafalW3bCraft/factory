"""Tests for the Switch-native FactoryOps workflow helpers."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from factory.factoryops import (
    FactoryOpsError,
    approval_record,
    can_publish_completion,
    create_demo,
    prepare_verifier_checkout,
)

FACTORY_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = FACTORY_ROOT / "switch" / "factoryops.template.yaml"


def git(directory: Path, *args: str) -> str:
    """Run git in a test fixture and return stdout."""
    return subprocess.run(
        ["git", "-C", str(directory), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class FactoryOpsDemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.factory_root = self.root / "factory"
        self.factory_root.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_demo_refuses_unsafe_roots(self) -> None:
        existing = self.root / "existing"
        existing.mkdir()
        (existing / "data.txt").write_text("keep", encoding="utf-8")

        for unsafe_path in (Path("relative"), self.factory_root, self.factory_root / "child", existing, Path("/")):
            with self.subTest(path=unsafe_path):
                with self.assertRaises(FactoryOpsError):
                    create_demo(unsafe_path, factory_root=self.factory_root)

        self.assertEqual((existing / "data.txt").read_text(encoding="utf-8"), "keep")

    def test_create_demo_creates_isolated_fixture_worktrees(self) -> None:
        paths = create_demo(self.root / "demo", factory_root=self.factory_root)

        self.assertTrue((paths.repository / ".git").exists())
        for worktree in (paths.builder, paths.inspector, paths.stresser):
            self.assertTrue((worktree / ".git").exists())
            self.assertEqual(git(worktree, "status", "--porcelain"), "")

        result = subprocess.run(
            ["python", "-m", "unittest", "discover", "-s", "tests"],
            cwd=paths.builder,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("test_positive_restock", result.stdout)
        self.assertIn("quantity", (paths.builder / "src" / "inventory.py").read_text(encoding="utf-8"))

    def test_prepare_verifier_checkout_detaches_at_the_candidate_commit(self) -> None:
        paths = create_demo(self.root / "demo", factory_root=self.factory_root)
        inventory = paths.builder / "src" / "inventory.py"
        inventory.write_text(
            inventory.read_text(encoding="utf-8").replace("self.quantity += amount", "if amount <= 0:\n            raise ValueError('amount must be positive')\n        self.quantity += amount"),
            encoding="utf-8",
        )
        git(paths.builder, "add", "src/inventory.py")
        git(paths.builder, "commit", "-m", "fix(inventory): reject nonpositive restock")
        candidate = git(paths.builder, "rev-parse", "HEAD")

        checked_out = prepare_verifier_checkout(paths.root, "inspector", candidate)

        self.assertEqual(checked_out, candidate)
        self.assertEqual(git(paths.inspector, "rev-parse", "HEAD"), candidate)
        self.assertNotEqual(
            subprocess.run(
                ["git", "-C", str(paths.inspector), "symbolic-ref", "-q", "HEAD"],
                check=False,
                capture_output=True,
                text=True,
            ).returncode,
            0,
        )

    def test_prepare_verifier_checkout_rejects_dirty_worktree_and_unknown_role(self) -> None:
        paths = create_demo(self.root / "demo", factory_root=self.factory_root)
        candidate = git(paths.builder, "rev-parse", "HEAD")
        (paths.inspector / "notes.txt").write_text("do not overwrite", encoding="utf-8")

        with self.assertRaises(FactoryOpsError):
            prepare_verifier_checkout(paths.root, "inspector", candidate)
        with self.assertRaises(FactoryOpsError):
            prepare_verifier_checkout(paths.root, "foreman", candidate)


class FactoryOpsGovernanceTests(unittest.TestCase):
    def test_approval_record_requires_a_later_plain_language_affirmative_reply(self) -> None:
        requested_at = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
        replied_at = requested_at + timedelta(minutes=1)
        record = approval_record(
            "a" * 40,
            "switch-user-demo",
            "Looks good — please publish the completion report.",
            requested_at,
            replied_at,
        )

        self.assertEqual(record.candidate_sha, "a" * 40)
        self.assertEqual(record.approver_id, "switch-user-demo")
        with self.assertRaises(FactoryOpsError):
            approval_record("a" * 40, "switch-user-demo", "Not approved", requested_at, replied_at)
        with self.assertRaises(FactoryOpsError):
            approval_record("a" * 40, "switch-user-demo", "Approved", requested_at, requested_at)

    def test_completion_requires_commit_both_independent_gates_and_approval(self) -> None:
        requested_at = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
        record = approval_record(
            "b" * 40,
            "switch-user-demo",
            "Yes, proceed.",
            requested_at,
            requested_at + timedelta(minutes=1),
        )

        self.assertTrue(can_publish_completion("b" * 40, "b" * 40, True, True, record))
        self.assertFalse(can_publish_completion("b" * 40, "a" * 40, True, True, record))
        self.assertFalse(can_publish_completion("b" * 40, "b" * 40, False, True, record))
        self.assertFalse(can_publish_completion("b" * 40, "b" * 40, True, False, record))
        self.assertFalse(can_publish_completion("a" * 40, "b" * 40, True, True, record))


class FactoryOpsTemplateTests(unittest.TestCase):
    def test_template_uses_four_safe_native_codex_agents(self) -> None:
        template = yaml.safe_load(TEMPLATE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(template["version"], 1)
        self.assertEqual(template["params"]["provider"]["default"], "codex")
        self.assertEqual(len(template["agents"]), 4)
        self.assertEqual(
            {agent["name"] for agent in template["agents"]},
            {"{team}-foreman", "{team}-smith", "{team}-inspector", "{team}-stresser"},
        )
        for agent in template["agents"]:
            self.assertEqual(agent["provider"], "{provider}")
            self.assertFalse(agent["auto_approve"])
            self.assertFalse(agent["auto_mode"])


if __name__ == "__main__":
    unittest.main()
