"""Regression tests for release verification and workspace creation boundaries."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def repository(path: Path) -> str:
    path.mkdir()
    git(path, "init", "-b", "candidate")
    git(path, "config", "user.name", "Regression Tests")
    git(path, "config", "user.email", "tests@factory.invalid")
    (path / "marker").write_text("first")
    git(path, "add", "marker")
    git(path, "-c", "core.hooksPath=/dev/null", "commit", "--no-gpg-sign", "-m", "test: first")
    return git(path, "rev-parse", "HEAD")


def verify(repo: Path, sha: str, *command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(ROOT / "scripts/verify-milestone.sh"), str(repo), sha, *command],
        capture_output=True,
        text=True,
    )


def test_verification_requires_command(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    sha = repository(repo)
    assert verify(repo, sha).returncode == 1


def test_verification_rejects_revision_other_than_head(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    first = repository(repo)
    (repo / "marker").write_text("second")
    git(repo, "commit", "-am", "test: second", "--no-gpg-sign")
    assert verify(repo, first, "true").returncode == 1


def test_verification_supports_worktrees_and_rechecks_mutations(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    sha = repository(repo)
    worktree = tmp_path / "worktree"
    git(repo, "worktree", "add", "--detach", str(worktree), sha)
    assert verify(worktree, sha, "true").returncode == 0
    assert verify(worktree, sha, "touch", "untracked-marker").returncode == 1


def test_bootstrap_preserves_nonempty_directory(tmp_path: Path) -> None:
    target = tmp_path / "workspace"
    target.mkdir()
    sentinel = target / "README.md"
    sentinel.write_text("must survive")
    result = subprocess.run(["bash", str(ROOT / "bootstrap-repo.sh"), str(target)], capture_output=True, text=True)
    assert result.returncode == 1
    assert sentinel.read_text() == "must survive"
    assert not (target / ".git").exists()


def test_bootstrap_rejects_nested_repository_and_symlink(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repository(repo)
    link = tmp_path / "link"
    link.symlink_to(repo, target_is_directory=True)
    for target in (repo / "nested", link / "nested"):
        result = subprocess.run(["bash", str(ROOT / "bootstrap-repo.sh"), str(target)], capture_output=True, text=True)
        assert result.returncode == 1
        assert not (repo / "nested").exists()


def test_legacy_host_execution_requires_explicit_unsafe_opt_in() -> None:
    env = dict(os.environ)
    env.pop("FACTORY_ALLOW_UNSAFE_HOST", None)
    result = subprocess.run(["bash", str(ROOT / "start-factory.sh")], env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "FACTORY_ALLOW_UNSAFE_HOST=1" in result.stderr
