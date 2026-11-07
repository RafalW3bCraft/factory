"""Guarded helpers for a human-governed Switch engineering demonstration."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

FACTORY_ROOT = Path(__file__).resolve().parents[2]
METADATA_FILE = ".factoryops-demo.json"
VERIFIER_ROLES = {"inspector", "stresser"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
AFFIRMATIVE_RE = re.compile(r"\b(approve(?:d)?|yes|proceed|go ahead|ship it|looks good)\b", re.IGNORECASE)
NEGATIVE_RE = re.compile(r"\b(not approved|do not|don't|reject(?:ed)?|no)\b", re.IGNORECASE)


class FactoryOpsError(ValueError):
    """Raised when a FactoryOps safety or workflow invariant is violated."""


@dataclass(frozen=True)
class DemoPaths:
    """Locations belonging to one managed disposable fixture."""

    root: Path
    repository: Path
    builder: Path
    inspector: Path
    stresser: Path
    baseline_sha: str


@dataclass(frozen=True)
class ApprovalRecord:
    """A human room approval associated with one candidate revision."""

    candidate_sha: str
    approver_id: str
    message: str
    requested_at: datetime
    recorded_at: datetime


def _fail(message: str) -> NoReturn:
    raise FactoryOpsError(message)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _managed_root(path: Path, factory_root: Path) -> Path:
    if not path.is_absolute():
        _fail("Demo root must be an absolute path.")

    root = path.resolve(strict=False)
    factory = factory_root.resolve()
    if root == Path("/") or root == factory or _is_within(root, factory) or _is_within(factory, root):
        _fail("Demo root must be outside the Factory repository and must not be a filesystem root or ancestor.")
    if root.exists() and any(root.iterdir()):
        _fail("Demo root already exists and is not empty; refusing to overwrite it.")
    return root


def _run_git(directory: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(directory), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "git command failed"
        _fail(f"Git operation failed: {detail}")
    return completed.stdout.strip()


def _write_fixture(repository: Path) -> None:
    (repository / "src").mkdir(parents=True)
    (repository / "tests").mkdir()
    (repository / "src" / "inventory.py").write_text(
        '''"""Deliberately flawed inventory fixture for the FactoryOps demo."""


class Inventory:
    def __init__(self, quantity: int = 0) -> None:
        self.quantity = quantity

    def restock(self, amount: int) -> None:
        self.quantity += amount
''',
        encoding="utf-8",
    )
    (repository / "tests" / "test_inventory.py").write_text(
        """import unittest

from src.inventory import Inventory


class InventoryTests(unittest.TestCase):
    def test_positive_restock(self) -> None:
        inventory = Inventory(2)
        inventory.restock(3)
        self.assertEqual(inventory.quantity, 5)


if __name__ == "__main__":
    unittest.main()
""",
        encoding="utf-8",
    )
    (repository / "ISSUE.md").write_text(
        "# Demo issue\n\nA negative restock quantity silently decrements inventory. "
        "Reject non-positive amounts without changing stock.\n",
        encoding="utf-8",
    )
    (repository / "README.md").write_text(
        "# FactoryOps disposable inventory fixture\n\nRun `python -m unittest discover -s tests`.\n",
        encoding="utf-8",
    )


def _write_metadata(paths: DemoPaths, candidate_sha: str | None = None) -> None:
    data: dict[str, str | int] = {"schema_version": 1, **{key: str(value) for key, value in asdict(paths).items()}}
    if candidate_sha is not None:
        data["candidate_sha"] = candidate_sha
    (paths.root / METADATA_FILE).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_demo(root: Path) -> DemoPaths:
    metadata_path = root.resolve() / METADATA_FILE
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        _fail(f"Managed FactoryOps demo metadata is unavailable: {exc}")
    if data.get("schema_version") != 1:
        _fail("Unsupported FactoryOps demo metadata schema.")
    required = ("root", "repository", "builder", "inspector", "stresser", "baseline_sha")
    if not all(isinstance(data.get(key), str) and data[key] for key in required):
        _fail("FactoryOps demo metadata is incomplete.")
    return DemoPaths(
        root=Path(data["root"]),
        repository=Path(data["repository"]),
        builder=Path(data["builder"]),
        inspector=Path(data["inspector"]),
        stresser=Path(data["stresser"]),
        baseline_sha=data["baseline_sha"],
    )


def create_demo(root: Path, *, factory_root: Path = FACTORY_ROOT) -> DemoPaths:
    """Create a disposable fixture repository and role-isolated worktrees."""
    demo_root = _managed_root(root, factory_root)
    demo_root.mkdir(parents=True, exist_ok=True)
    repository = demo_root / "repository"
    repository.mkdir()
    _run_git(repository, "init", "-b", "main")
    _run_git(repository, "config", "user.name", "FactoryOps Demo")
    _run_git(repository, "config", "user.email", "demo@factory.invalid")
    _write_fixture(repository)
    _run_git(repository, "add", ".")
    _run_git(repository, "commit", "--no-gpg-sign", "-m", "chore: seed disposable inventory fixture")
    baseline_sha = _run_git(repository, "rev-parse", "HEAD")

    worktrees = {role: demo_root / role for role in ("builder", "inspector", "stresser")}
    for role, worktree in worktrees.items():
        _run_git(repository, "worktree", "add", "-b", f"factoryops/{role}", str(worktree), baseline_sha)

    paths = DemoPaths(root=demo_root, repository=repository, baseline_sha=baseline_sha, **worktrees)
    _write_metadata(paths)
    return paths


def _set_writable(root: Path) -> None:
    for current, directories, files in os.walk(root, topdown=False):
        for filename in files:
            path = Path(current, filename)
            path.chmod(path.stat().st_mode | stat.S_IWUSR)
        for dirname in directories:
            path = Path(current, dirname)
            path.chmod(path.stat().st_mode | stat.S_IWUSR)
    root.chmod(root.stat().st_mode | stat.S_IWUSR)


def _set_read_only(root: Path) -> None:
    write_bits = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    for current, directories, files in os.walk(root, topdown=False):
        for filename in files:
            path = Path(current, filename)
            path.chmod(path.stat().st_mode & ~write_bits)
        for dirname in directories:
            path = Path(current, dirname)
            path.chmod(path.stat().st_mode & ~write_bits)
    root.chmod(root.stat().st_mode & ~write_bits)


def prepare_verifier_checkout(root: Path, role: str, candidate_sha: str) -> str:
    """Detach a clean verifier worktree at a reachable candidate commit."""
    if role not in VERIFIER_ROLES:
        _fail(f"Verifier role must be one of: {', '.join(sorted(VERIFIER_ROLES))}.")
    if not SHA_RE.fullmatch(candidate_sha):
        _fail("Candidate SHA must be a full lowercase 40-character commit SHA.")

    paths = _load_demo(root)
    verifier = getattr(paths, role)
    _set_writable(verifier)
    if _run_git(verifier, "status", "--porcelain"):
        _fail(f"Verifier worktree for {role} is dirty; refusing to replace evidence.")
    _run_git(paths.repository, "rev-parse", "--verify", f"{candidate_sha}^{{commit}}")
    _run_git(verifier, "checkout", "--detach", candidate_sha)
    _set_read_only(verifier)
    _write_metadata(paths, candidate_sha)
    return candidate_sha


def approval_record(
    candidate_sha: str,
    approver_id: str,
    message: str,
    requested_at: datetime,
    replied_at: datetime,
) -> ApprovalRecord:
    """Validate and represent a linked human's post-request approval."""
    if not SHA_RE.fullmatch(candidate_sha):
        _fail("Approval must name a full lowercase 40-character candidate SHA.")
    if not approver_id.strip():
        _fail("Approval must include the linked Switch human identity.")
    if requested_at.tzinfo is None or replied_at.tzinfo is None or replied_at <= requested_at:
        _fail("Approval reply must have a timezone and be later than the approval request.")
    if NEGATIVE_RE.search(message) or not AFFIRMATIVE_RE.search(message):
        _fail("Approval reply is not an unambiguous plain-language affirmative.")
    return ApprovalRecord(candidate_sha, approver_id, message.strip(), requested_at, replied_at.astimezone(UTC))


def can_publish_completion(
    candidate_sha: str,
    smith_commit_sha: str,
    inspector_passed: bool,
    stresser_passed: bool,
    approval: ApprovalRecord | None,
) -> bool:
    """Return whether every required human-governance gate has passed."""
    return bool(
        SHA_RE.fullmatch(candidate_sha)
        and candidate_sha == smith_commit_sha
        and inspector_passed
        and stresser_passed
        and approval is not None
        and approval.candidate_sha == candidate_sha
    )


def main(argv: list[str] | None = None) -> int:
    """Run the guarded FactoryOps fixture and verifier commands."""
    parser = argparse.ArgumentParser(description="FactoryOps disposable demo helpers")
    subcommands = parser.add_subparsers(dest="command", required=True)
    init = subcommands.add_parser("init-demo", help="create a disposable fixture and worktrees")
    init.add_argument("--root", required=True, type=Path, help="new absolute demo root outside this repository")
    verifier = subcommands.add_parser("prepare-verifier", help="detach a verifier at a candidate SHA")
    verifier.add_argument("--root", required=True, type=Path, help="managed demo root")
    verifier.add_argument("--role", required=True, choices=sorted(VERIFIER_ROLES))
    verifier.add_argument("--commit", required=True, help="full candidate commit SHA")
    args = parser.parse_args(argv)

    try:
        if args.command == "init-demo":
            paths = create_demo(args.root)
            print(json.dumps({key: str(value) for key, value in asdict(paths).items()}, sort_keys=True))
        else:
            candidate = prepare_verifier_checkout(args.root, args.role, args.commit)
            print(json.dumps({"candidate_sha": candidate, "role": args.role}, sort_keys=True))
    except FactoryOpsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def run_cli() -> None:
    """Console-script entry point."""
    raise SystemExit(main())
