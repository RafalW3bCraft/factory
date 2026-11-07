"""Real Git export and bounded-process tests; container tests require an engine."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from factory.factoryops import create_demo
from factory.verification import VerificationError, container_command, run_bounded, snapshot_candidate, verify_candidate
from factory.workflow import Ledger


def test_snapshot_exports_only_exact_committed_candidate_without_credentials(tmp_path: Path) -> None:
    paths = create_demo(tmp_path / "fixture")
    (paths.builder / ".switch").mkdir()
    (paths.builder / ".switch" / "credential.json").write_text("DO_NOT_EXPORT")
    # Ignored native runtime credentials may exist, but never enter the archive.
    info = paths.repository / ".git" / "info" / "exclude"
    info.write_text(info.read_text() + "\n.switch/\n")
    result = snapshot_candidate(paths.builder, paths.baseline_sha, tmp_path / "snapshot")
    assert len(result) == 64
    assert not (tmp_path / "snapshot" / ".git").exists()
    assert not (tmp_path / "snapshot" / ".switch").exists()
    assert (tmp_path / "snapshot" / "src" / "inventory.py").exists()
    (paths.builder / "extra.txt").write_text("dirty")
    with pytest.raises(VerificationError):
        snapshot_candidate(paths.builder, paths.baseline_sha, tmp_path / "dirty-snapshot")


def test_snapshot_rejects_wrong_revision_and_symlink(tmp_path: Path) -> None:
    paths = create_demo(tmp_path / "fixture")
    with pytest.raises(VerificationError):
        snapshot_candidate(paths.builder, "a" * 40, tmp_path / "missing")
    (paths.builder / "escape").symlink_to(tmp_path / "external")
    subprocess.run(["git", "-C", str(paths.builder), "add", "escape"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(paths.builder), "commit", "-m", "test: link"], check=True, capture_output=True)
    candidate = subprocess.check_output(["git", "-C", str(paths.builder), "rev-parse", "HEAD"], text=True).strip()
    with pytest.raises(VerificationError):
        snapshot_candidate(paths.builder, candidate, tmp_path / "linked")
    assert not (tmp_path / "linked").exists()


def test_bounded_execution_timeout_output_limit_and_descendant_cleanup(tmp_path: Path) -> None:
    normal = run_bounded([sys.executable, "-c", "print('local fixture')"], timeout=2, output_limit=1000)
    assert normal["exit_code"] == 0
    assert normal["output"] == "local fixture\n"
    noisy = run_bounded([sys.executable, "-c", "print('x'*1000000)"], timeout=2, output_limit=1000)
    assert noisy["limited"] is True
    assert len(str(noisy["output"])) <= 1000
    timed = run_bounded([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.1, output_limit=1000)
    assert timed["limited"] is True
    assert timed["exit_code"] != 0
    assert os.getpgid(os.getpid()) != timed["process_group"]


def test_container_command_has_no_host_credentials_and_enforced_limits(tmp_path: Path) -> None:
    command = container_command(
        "/bin/docker", "sha256:" + "a" * 64, tmp_path, "fixture-check", ["python", "-m", "unittest"]
    )
    rendered = " ".join(command)
    for flag in (
        "--network=none",
        "--read-only",
        "--user=65534:65534",
        "--cap-drop=ALL",
        "--pids-limit=64",
        "--memory=256m",
        "--cpus=1",
        "no-new-privileges",
        "readonly",
    ):
        assert flag in rendered
    assert "docker.sock" not in rendered
    assert ".codex" not in rendered
    assert str(Path.home()) not in rendered.replace(str(tmp_path), "")
    with pytest.raises(VerificationError):
        container_command("/bin/docker", "python:latest", tmp_path, "test", ["python"])


@pytest.mark.parametrize("bare_id", [True, False])
def test_runner_receipts_and_failed_recheck_use_real_snapshot_mocked_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bare_id: bool
) -> None:
    """Engine results are simulated; this test asserts orchestration, NOT containment."""
    import factory.verification as verification

    paths = create_demo(tmp_path / "fixture")
    store = Ledger(
        tmp_path / "controller",
        room_id="room",
        owner_id="human",
        seats={"inspector": "inspector", "stresser": "stresser"},
    )
    original = verification.run_bounded
    image = "sha256:" + "a" * 64
    fail = False
    observed: list[list[str]] = []

    def execute(command: list[str], **kwargs: Any) -> dict:
        if command[0] == "git":
            return original(command, **kwargs)
        observed.append(command)
        output = (
            (image[7:] if bare_id else image) + "\n"
            if command[1] == "image"
            else ""
            if command[1] == "ps"
            else "simulated container output"
        )
        if command[1] == "image":
            output = "Emulate Docker CLI using podman.\n" + output
        return {
            "exit_code": 1 if fail and command[1] == "run" else 0,
            "output": output,
            "duration_seconds": 0.01,
            "limited": False,
        }

    monkeypatch.setattr(verification, "run_bounded", execute)
    monkeypatch.setattr(verification.shutil, "which", lambda name: "/simulated/docker")
    receipt = verify_candidate(store, "inspector", paths.builder, paths.baseline_sha, image=image)
    assert receipt["exit_code"] == 0
    assert any(command[1:3] == ["rm", "--force"] for command in observed)
    assert observed[-1][1:3] == ["ps", "--all"]
    fail = True
    with pytest.raises(VerificationError):
        verify_candidate(store, "inspector", paths.builder, paths.baseline_sha, image=image)
    assert "inspector" not in store.status()["receipts"]
    assert len(list(store.directory.glob("factoryops-verify-*.json"))) == 2
    monkeypatch.setattr(verification.shutil, "which", lambda name: None)
    with pytest.raises(VerificationError):
        verify_candidate(store, "stresser", paths.builder, paths.baseline_sha, image=image)


def test_timeout_callback_exception_still_reaps_process(tmp_path: Path) -> None:
    import signal

    pidfile = tmp_path / "child.pid"
    command = [
        sys.executable,
        "-c",
        'import os,sys,time; open(sys.argv[1],"w").write(str(os.getpid())); time.sleep(30)',
        str(pidfile),
    ]

    def broken_cleanup() -> None:
        raise RuntimeError("simulated engine cleanup launch failure")

    try:
        with pytest.raises(RuntimeError):
            run_bounded(command, timeout=0.3, on_limit=broken_cleanup)
        pid = int(pidfile.read_text())
        assert not Path("/proc", str(pid)).exists(), "cleanup callback exception left process alive"
    finally:
        if pidfile.exists():
            pid = int(pidfile.read_text())
            try:
                os.killpg(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass


def test_unknown_container_cleanup_withholds_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import factory.verification as verification

    paths = create_demo(tmp_path / "fixture")
    store = Ledger(tmp_path / "controller", room_id="room", owner_id="human", seats={"inspector": "i", "stresser": "s"})
    original = verification.run_bounded
    image = "sha256:" + "a" * 64

    def engine(command: list[str], **kwargs: Any) -> dict:
        if command[0] == "git":
            return original(command, **kwargs)
        output = image if command[1] == "image" else ""
        return {
            "exit_code": 1 if command[1] in ("rm", "ps") else 0,
            "output": output,
            "limited": False,
            "duration_seconds": 0.01,
        }

    monkeypatch.setattr(verification, "run_bounded", engine)
    monkeypatch.setattr(verification.shutil, "which", lambda _: "/simulated/docker")
    with pytest.raises(VerificationError):
        verify_candidate(store, "inspector", paths.builder, paths.baseline_sha, image=image)
    assert "inspector" not in store.status()["receipts"]


def test_snapshot_cannot_substitute_git_replace_blobs(tmp_path: Path) -> None:
    paths = create_demo(tmp_path / "fixture")
    source = paths.builder / "src/inventory.py"
    original = source.read_bytes()
    blob = subprocess.check_output(
        ["git", "-C", str(paths.builder), "rev-parse", "HEAD:src/inventory.py"], text=True
    ).strip()
    replacement = (
        subprocess.check_output(
            ["git", "-C", str(paths.builder), "hash-object", "-w", "--stdin"], input=b"REPLACED CANDIDATE\n"
        )
        .decode()
        .strip()
    )
    subprocess.run(["git", "-C", str(paths.builder), "replace", blob, replacement], check=True, capture_output=True)
    snapshot_candidate(paths.builder, paths.baseline_sha, tmp_path / "snapshot")
    assert (tmp_path / "snapshot/src/inventory.py").read_bytes() == original
