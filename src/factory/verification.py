"""Exact-revision exports and credential-free, bounded container verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from factory.workflow import Ledger, WorkflowError

MAX_ARCHIVE = 16 * 1024 * 1024
MAX_OUTPUT = 64 * 1024
CLEAN_ENV = {
    "PATH": os.defpath,
    "HOME": "/nonexistent",
    "LANG": "C.UTF-8",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_NO_REPLACE_OBJECTS": "1",
}
INSPECTOR_COMMAND = ["python", "-B", "-m", "unittest", "discover", "-s", "tests"]
STRESSER_COMMAND = [
    "python",
    "-B",
    "-c",
    """from src.inventory import Inventory
for amount in (0, -1, -1000000):
    inventory = Inventory(7)
    try:
        inventory.restock(amount)
    except ValueError:
        assert inventory.quantity == 7, 'rejection changed inventory'
    else:
        raise AssertionError('nonpositive amount accepted')
inventory = Inventory(7)
inventory.restock(3)
assert inventory.quantity == 10
print('boundary checks passed')
""",
]


class VerificationError(WorkflowError):
    """Exact content or execution containment could not be established."""


def engine_environment() -> dict[str, str]:
    """Trusted local engine configuration only; never inherited by container code."""
    result = {**CLEAN_ENV, "HOME": str(Path.home()), "DOCKER_HOST": "unix:///var/run/docker.sock"}
    if "XDG_RUNTIME_DIR" in os.environ:
        result["XDG_RUNTIME_DIR"] = os.environ["XDG_RUNTIME_DIR"]
    return result


def run_bounded(
    command: list[str],
    *,
    timeout: float = 30,
    output_limit: int = MAX_OUTPUT,
    cwd: Path | None = None,
    environment: dict[str, str] | None = None,
    on_limit: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Bound trusted process orchestration. Untrusted code requires the container backend."""
    if not command or timeout <= 0 or output_limit <= 0:
        raise VerificationError("Execution requires an argv, positive timeout and output limit.")
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=CLEAN_ENV if environment is None else environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    assert process.stdout is not None
    output = bytearray()
    limited = False
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while selector.get_map():
            if time.monotonic() - started >= timeout:
                limited = True
                break
            for key, _ in selector.select(min(0.05, timeout)):
                chunk = os.read(key.fd, 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                remaining = output_limit - len(output)
                output.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    limited = True
                    break
            if limited:
                break
        if not limited:
            try:
                process.wait(timeout=max(0.01, timeout - (time.monotonic() - started)))
            except subprocess.TimeoutExpired:
                limited = True
    finally:
        selector.close()
        try:
            if limited and on_limit is not None:
                # Stop the container before terminating its attached CLI/monitor.
                on_limit()
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            process.stdout.close()

    return {
        "exit_code": process.returncode if not limited else 124,
        "limited": limited,
        "duration_seconds": round(time.monotonic() - started, 6),
        "output": output.decode("utf-8", errors="replace"),
        "process_group": process.pid,
    }


def _git_arguments(repository: Path, *arguments: str) -> list[str]:
    """Trust one canonical repository for read-only inspection, never a wildcard."""
    if (
        not repository.is_absolute()
        or ".." in repository.parts
        or "*" in str(repository)
        or any(path.is_symlink() for path in (repository, *repository.parents))
        or not repository.is_dir()
    ):
        raise VerificationError("Candidate Git inspection requires one canonical, non-symlink repository.")
    return [
        "git",
        "--no-pager",
        "-c",
        "safe.directory=",
        "-c",
        f"safe.directory={repository}",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-C",
        str(repository),
        *arguments,
    ]


def _git(repository: Path, *arguments: str) -> str:
    result = run_bounded(
        _git_arguments(repository, *arguments),
        timeout=10,
        output_limit=MAX_ARCHIVE,
    )
    if result["exit_code"] != 0:
        raise VerificationError("Git candidate inspection failed; no candidate code executed.")
    return str(result["output"]).strip()


def snapshot_candidate(repository: Path, candidate_sha: str, destination: Path) -> str:
    """Export regular committed files only; exclude .git, .switch, hooks and credentials."""
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_sha):
        raise VerificationError("A full candidate commit SHA is required.")
    if not repository.is_absolute() or any(p.is_symlink() for p in (repository, *repository.parents)):
        raise VerificationError("Candidate repository must have a canonical, non-symlink path.")
    if destination.exists() or destination.is_symlink():
        raise VerificationError("Snapshot destination must be new.")
    if _git(repository, "rev-parse", "HEAD") != candidate_sha or _git(
        repository, "status", "--porcelain", "--untracked-files=all"
    ):
        raise VerificationError("Candidate HEAD must match the requested revision and be clean.")
    entries = _git(repository, "ls-tree", "-r", "--full-tree", candidate_sha).splitlines()
    if not entries or len(entries) > 1000:
        raise VerificationError("Candidate must contain between 1 and 1000 regular files.")
    files: list[tuple[Path, str, int, int]] = []
    total_size = 0
    for line in entries:
        try:
            header, name = line.split("\t", 1)
            git_mode, kind, object_id = header.split()
            path = Path(name)
            if (
                git_mode not in ("100644", "100755")
                or kind != "blob"
                or not re.fullmatch(r"[0-9a-f]{40}", object_id)
                or name.startswith('"')
                or path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or any(part in (".git", ".switch", ".codex") or part.startswith(".env") for part in path.parts)
            ):
                raise ValueError
            size = int(_git(repository, "cat-file", "-s", object_id))
            total_size += size
            if size < 0 or total_size > MAX_ARCHIVE:
                raise ValueError
            files.append((path, object_id, 0o555 if git_mode == "100755" else 0o444, size))
        except (ValueError, TypeError) as exc:
            raise VerificationError(
                "Candidate contains unsafe paths, links, credentials or excessive content."
            ) from exc
    # Read exact Git blobs: archive attributes/filters cannot omit or substitute content.
    manifest: list[tuple[str, str, int]] = []
    destination.mkdir(mode=0o755)
    try:
        for path, object_id, mode, size in files:
            result = subprocess.run(
                _git_arguments(repository, "cat-file", "blob", object_id),
                capture_output=True,
                check=False,
                timeout=10,
                env=CLEAN_ENV,
            )
            if result.returncode != 0 or len(result.stdout) != size:
                raise VerificationError("Git blob changed or was unavailable during export.")
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(result.stdout)
            target.chmod(mode)
            manifest.append((str(path), hashlib.sha256(result.stdout).hexdigest(), mode))
        if _git(repository, "rev-parse", "HEAD") != candidate_sha or _git(
            repository, "status", "--porcelain", "--untracked-files=all"
        ):
            raise VerificationError("Candidate changed during snapshot preparation.")
    except BaseException:
        shutil.rmtree(destination)
        raise
    return hashlib.sha256(json.dumps(sorted(manifest), separators=(",", ":")).encode()).hexdigest()


def container_command(engine: str, image: str, snapshot: Path, name: str, command: list[str]) -> list[str]:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image) or not command:
        raise VerificationError("Verification requires an immutable local image ID and an explicit command.")
    if any(c in str(snapshot) for c in (",", "\n", "\r")):
        raise VerificationError("Snapshot path cannot contain container mount separators.")
    return [
        engine,
        "run",
        "--rm",
        "--name",
        name,
        "--pull=never",
        "--network=none",
        "--stop-timeout=0",
        "--read-only",
        "--user=65534:65534",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--memory=256m",
        "--memory-swap=256m",
        "--cpus=1",
        "--ulimit=nofile=256:256",
        "--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777",
        "--mount",
        f"type=bind,src={snapshot},dst=/candidate,readonly",
        "--workdir=/candidate",
        "--env=HOME=/tmp",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        "--entrypoint=",
        image,
        *command,
    ]


def cleanup_command(engine: str, name: str) -> list[str]:
    """Podman force-removal defaults to a ten-second grace; request immediate stop."""
    version = run_bounded([engine, "--version"], timeout=3, environment=engine_environment())
    podman = "podman version" in str(version["output"]).lower()
    return [engine, "rm", "--force", *(["--time=0", "--ignore"] if podman else []), name]


def verify_candidate(
    store: Ledger,
    role: str,
    repository: Path,
    candidate_sha: str,
    *,
    image: str,
    engine: str = "docker",
    timeout: float = 30,
) -> dict[str, Any]:
    """Only actual successful contained execution may issue an accepted receipt."""
    state = store.status()
    generation = None
    if state["candidate_sha"] is not None:
        generation = store.begin_verification(role)
    with tempfile.TemporaryDirectory(prefix="snapshot-", dir=store.directory) as temporary:
        # The container can read the single snapshot, never its private parent/key.
        snapshot = Path(temporary) / "candidate"
        manifest = snapshot_candidate(repository, candidate_sha, snapshot)
        if state["candidate_sha"] is None:
            store.set_candidate(candidate_sha, manifest, expected_revision=state["revision"])
            generation = None
        elif (state["candidate_sha"], state["manifest"]) != (candidate_sha, manifest):
            store.set_candidate(candidate_sha, manifest, expected_revision=state["revision"])
            generation = None
        if generation is None:
            generation = store.begin_verification(role)
        executable = shutil.which(engine)
        if executable is None:
            raise VerificationError("Container engine is missing; no host fallback is permitted.")
        check = run_bounded(
            [executable, "image", "inspect", "--format={{.Id}}", image], timeout=10, environment=engine_environment()
        )
        # The distro's Docker compatibility wrapper emits a notice on stderr.
        # Accept exactly one complete immutable ID line, never a substring of an error.
        identifiers = [
            line.strip()
            for line in str(check["output"]).splitlines()
            if re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", line.strip())
        ]
        inspected = identifiers[0] if len(identifiers) == 1 else ""
        if re.fullmatch(r"[0-9a-f]{64}", inspected):
            inspected = "sha256:" + inspected
        if check["exit_code"] != 0 or inspected != image:
            raise VerificationError("Immutable verification image is unavailable; build it before retrying.")
        name = "factoryops-verify-" + uuid.uuid4().hex
        command = INSPECTOR_COMMAND if role == "inspector" else STRESSER_COMMAND
        argv = container_command(executable, image, snapshot, name, command)

        def remove_container() -> None:
            run_bounded(cleanup_command(executable, name), timeout=10, environment=engine_environment())

        execution_error: BaseException | None = None
        execution_started = time.monotonic()
        try:
            result = run_bounded(argv, timeout=timeout, environment=engine_environment(), on_limit=remove_container)
        except BaseException as exc:
            execution_error = exc
            result = {
                "exit_code": 125,
                "duration_seconds": time.monotonic() - execution_started,
                "output": "Supervisor failure: " + type(exc).__name__,
            }
        try:
            cleanup = run_bounded(cleanup_command(executable, name), timeout=10, environment=engine_environment())
        except Exception:
            cleanup = {"exit_code": 125}
        try:
            presence = run_bounded(
                [executable, "ps", "--all", "--filter", "name=" + name, "--format={{.Names}}"],
                timeout=10,
                environment=engine_environment(),
            )
        except Exception:
            presence = {"exit_code": 125, "output": "cleanup status unavailable"}
        remaining = [
            line.strip()
            for line in str(presence["output"]).splitlines()
            if line.strip() and not line.startswith("Emulate Docker CLI using podman.")
        ]
        cleanup_confirmed = presence["exit_code"] == 0 and not remaining
        body = {
            **generation,
            "role": role,
            "command": command,
            "exit_code": result["exit_code"],
            "duration_seconds": result["duration_seconds"],
            "output_sha256": hashlib.sha256(str(result["output"]).encode()).hexdigest(),
            "backend": "container",
            "isolated": True,
            "image": image,
            "cleanup_exit_code": cleanup["exit_code"],
            "cleanup_confirmed": cleanup_confirmed,
        }
        # Preserve bounded evidence on failed runs, without importing caller PASS flags.
        evidence = store.directory / (name + ".json")
        descriptor = os.open(evidence, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            json.dump({"receipt": body, "output": result["output"]}, output, sort_keys=True)
            output.flush()
            os.fsync(output.fileno())
        if not cleanup_confirmed:
            retained = store.directory / (name + "-unconfirmed-cleanup")
            Path(temporary).rename(retained)
            if isinstance(execution_error, (KeyboardInterrupt, SystemExit)):
                raise execution_error
            raise VerificationError("Container removal could not be confirmed; snapshot and evidence retained.")
        if isinstance(execution_error, (KeyboardInterrupt, SystemExit)):
            raise execution_error
        if result["exit_code"] != 0:
            raise VerificationError(f"{role} failed (exit {result['exit_code']}); bounded evidence retained.")
        receipt = store._seal_receipt(body)
        store.record_receipt(receipt)
        return receipt
