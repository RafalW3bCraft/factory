"""Real local process ownership and descendant shutdown regression tests."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from factory.process_identity import capture, stop_owned, write_record


def test_changed_identity_cannot_stop_unrelated_python(tmp_path: Path) -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        record = capture(child.pid, group=False)
        record["start_time"] += 1
        path = tmp_path / "foreman.identity.json"
        write_record(path, record)
        assert not stop_owned(path, timeout=0.1)
        assert child.poll() is None
    finally:
        child.terminate()
        child.wait(timeout=3)


def test_owned_process_group_stops_descendants(tmp_path: Path) -> None:
    marker = tmp_path / "child-pid"
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); open(sys.argv[1],'w').write(str(p.pid)); time.sleep(30)",
            str(marker),
        ],
        start_new_session=True,
    )
    try:
        for _ in range(100):
            if marker.exists():
                break
            time.sleep(0.01)
        descendant = int(marker.read_text())
        path = tmp_path / "foreman.identity.json"
        write_record(path, capture(child.pid, group=True))
        assert stop_owned(path, timeout=0.5)
        child.wait(timeout=3)
        status = Path(f"/proc/{descendant}/stat")
        assert not status.exists() or status.read_text().split(") ", 1)[1].startswith("Z ")
    finally:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=3)


def test_crashed_group_leader_still_cleans_recorded_descendants(tmp_path: Path) -> None:
    marker = tmp_path / "child-pid"
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); open(sys.argv[1],'w').write(str(p.pid)); time.sleep(30)",
            str(marker),
        ],
        start_new_session=True,
    )
    try:
        for _ in range(100):
            if marker.exists():
                break
            time.sleep(0.01)
        descendant = int(marker.read_text())
        path = tmp_path / "foreman.identity.json"
        write_record(path, capture(child.pid, group=True))
        child.kill()
        child.wait(timeout=3)
        assert stop_owned(path, timeout=0.1)
        for _ in range(100):
            status = Path(f"/proc/{descendant}/stat")
            if not status.exists() or status.read_text().split(") ", 1)[1].startswith("Z "):
                break
            time.sleep(0.01)
        else:
            raise AssertionError("Recorded descendant survived leader crash")
    finally:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=3)
