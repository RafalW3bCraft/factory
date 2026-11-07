"""Real Linux UID boundary probe in a disposable container, not host deployment proof.

Run this trusted harness as container root with only CHOWN/SETUID/SETGID/DAC_OVERRIDE.
It creates synthetic state and fixture data, never provider credentials.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path

from factory.factoryops import (
    FactoryOpsError,
    _run_git,
    create_demo,
    load_demo_readonly,
    prepare_verifier_checkout,
)
from factory.verification import snapshot_candidate
from factory.workflow import Ledger


def as_user(uid: int, action: Callable[[], None]) -> None:
    pid = os.fork()
    if pid == 0:
        try:
            os.setgroups([5000])
            os.setgid(5000)
            os.setuid(uid)
            action()
        except BaseException as exc:
            print(json.dumps({"phase_uid": uid, "error_type": type(exc).__name__}), flush=True)
            os._exit(1)
        os._exit(0)
    _, status = os.waitpid(pid, 0)
    if os.waitstatus_to_exitcode(status) != 0:
        raise RuntimeError("Disposable principal probe failed.")


def main() -> int:
    if os.getuid() != 0:
        raise RuntimeError("This probe requires disposable container root, never host sudo.")
    base = Path(tempfile.mkdtemp(prefix="factoryops-principals-"))
    base.chmod(0o755)
    fixture = base / "fixture"
    fixture.mkdir()
    os.chown(fixture, 1000, 5000)
    controller = base / "controller"
    controller.mkdir(mode=0o700)
    os.chown(controller, 1001, 5000)
    candidate_record = base / "candidate.txt"
    candidate_record.touch(mode=0o600)
    os.chown(candidate_record, 1000, 5000)

    def prepare() -> None:
        paths = create_demo(fixture, factory_root=Path("/trusted"))
        target = paths.builder / "src/inventory.py"
        target.write_text(
            target.read_text().replace(
                "        self.quantity += amount",
                "        if amount <= 0:\n            raise ValueError('positive amount required')\n        self.quantity += amount",
            )
        )
        _run_git(paths.builder, "add", "src/inventory.py")
        _run_git(paths.builder, "commit", "--no-gpg-sign", "-m", "fix: reject nonpositive restocks")
        sha = _run_git(paths.builder, "rev-parse", "HEAD")
        for role in ("inspector", "stresser"):
            prepare_verifier_checkout(fixture, role, sha)
        candidate_record.write_text(sha)
        candidate_record.chmod(0o640)
        # Grant the controller group read/search, preserving owner and executable bits.
        for path in [fixture, *fixture.rglob("*")]:
            mode = stat.S_IMODE(path.stat().st_mode)
            path.chmod(mode | 0o040 | (0o010 if path.is_dir() else 0))

    as_user(1000, prepare)

    def inspect() -> None:
        paths = load_demo_readonly(fixture, expected_owner_uid=1000)
        sha = candidate_record.read_text()
        manifest = snapshot_candidate(paths.builder, sha, controller / "snapshot")
        assert len(manifest) == 64
        try:
            prepare_verifier_checkout(fixture, "inspector", sha)
        except FactoryOpsError:
            pass
        else:
            raise AssertionError("Controller unexpectedly mutated agent-owned preparation.")
        store = Ledger(
            controller / "state", room_id="room", owner_id="human", seats={"inspector": "i", "stresser": "s"}
        )
        store.set_candidate(sha, manifest)
        (controller / "report-sentinel.json").write_text('{"synthetic":true}')

    as_user(1001, inspect)

    def denied() -> None:
        targets = [
            controller / "state/receipt.key",
            controller / "state/workflow.sqlite3",
            controller / "report-sentinel.json",
        ]
        for path in targets:
            for mode in ("rb", "ab"):
                try:
                    with path.open(mode):
                        pass
                except PermissionError:
                    pass
                else:
                    raise AssertionError("Agent accessed controller-private state.")

    as_user(1000, denied)
    print(
        json.dumps(
            {
                "controller_uid": 1001,
                "source_uid": 1000,
                "foreign_source_read": True,
                "controller_mutation_denied": True,
                "agent_key_database_report_access_denied": True,
                "provider_credentials_used": False,
                "scope": "disposable-container-two-uid; host/native deployment unverified",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
