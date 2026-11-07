"""Linux process ownership records for the explicitly unsafe legacy host runner.

PID numbers or command-name substrings are never sufficient authorization to
signal a process. Dedicated sessions bound ordinary descendant processes.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import tempfile
import time
from pathlib import Path
from typing import Any


def capture(pid: int, *, group: bool) -> dict[str, Any]:
    """Capture kernel identity, including boot and start time, without secrets."""
    if pid <= 1:
        raise ValueError("Unsafe process identifier")
    proc = Path(f"/proc/{pid}")
    fields = (proc / "stat").read_text().rsplit(") ", 1)[1].split()
    if fields[0] == "Z":
        raise ProcessLookupError(pid)
    identity = {
        "pid": pid,
        "uid": proc.stat().st_uid,
        "start_time": int(fields[19]),
        "pgid": int(fields[2]),
        "sid": int(fields[3]),
        "group": group,
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
    }
    if identity["uid"] != os.getuid():
        raise ValueError("Process belongs to another user")
    if group and (identity["pgid"] != pid or identity["sid"] != pid):
        raise ValueError("Child must have its own process session")
    return identity


def write_record(path: Path, record: dict[str, Any]) -> None:
    """Atomically publish a private identity record in a private directory."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Symlink process records are forbidden")
    record = dict(record)
    if record.get("group"):
        record["members"] = _group_members(record)
    fd, temporary = tempfile.mkstemp(prefix=".identity-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(record, output, sort_keys=True)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _matches(record: dict[str, Any]) -> bool:
    try:
        current = capture(record["pid"], group=record["group"])
        return all(record.get(key) == value for key, value in current.items())
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _group_members(record: dict[str, Any]) -> list[dict[str, Any]]:
    members = []
    for proc in Path("/proc").iterdir():
        if proc.name.isdecimal():
            try:
                member = capture(int(proc.name), group=False)
                if member["pgid"] == record["pid"] and member["sid"] == record["pid"]:
                    members.append(member)
            except (OSError, ValueError):
                continue
    return members


def stop_owned(path: Path, *, timeout: float = 5.0) -> bool:
    """Signal only a still-matching process identity and its dedicated group."""
    if path.is_symlink():
        return False
    try:
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            return False
        record = json.loads(path.read_text())
        if record.get("pid") == os.getpid():
            return False
        if not _matches(record):
            # A crashed leader cannot authorize an arbitrary current process
            # group. Only independently recorded, still-identical descendants
            # can be stopped in this case; a recycled PID is never touched.
            stopped = False
            for member in record.get("members", []):
                if member.get("pid") != record.get("pid") and _matches(member):
                    os.kill(member["pid"], signal.SIGKILL)
                    stopped = True
            return stopped
        pid = record["pid"]
        send = os.killpg if record["group"] else os.kill
        send(pid, signal.SIGTERM)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and _matches(record):
            time.sleep(0.02)
        # A dead leader can leave a descendant in its original session. Session
        # IDs remain reserved while members exist; inspect all members before
        # cleanup rather than signalling a possibly reused PID.
        if record["group"]:
            members = _group_members(record)
            for member in members:
                if member["start_time"] >= record["start_time"] and member["boot_id"] == record["boot_id"]:
                    if _matches(member):
                        os.kill(member["pid"], signal.SIGKILL)
        elif _matches(record):
            os.kill(pid, signal.SIGKILL)
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False
    finally:
        path.unlink(missing_ok=True)


def main() -> None:
    """Small shell-compatible process record interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("record", "stop"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--group", action="store_true")
    args = parser.parse_args()
    if args.action == "record":
        if args.pid is None:
            parser.error("--pid is required")
        for attempt in range(50):
            try:
                write_record(args.path, capture(args.pid, group=args.group))
                break
            except (OSError, ValueError):
                if attempt == 49:
                    parser.exit(1, "ERROR: Child identity could not be established.\n")
                time.sleep(0.01)
    else:
        stop_owned(args.path)


if __name__ == "__main__":
    main()
