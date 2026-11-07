"""Credential-free local runtime smoke; never evidence of live integration."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from factory.config import asset_directory
from factory.factoryops import create_demo


def main() -> int:
    if os.getuid() == 0:
        print("ERROR: Sandbox smoke must run as a non-root user.", file=sys.stderr)
        return 1
    asset_directory("mandates")
    asset_directory("dispatch")
    with tempfile.TemporaryDirectory(prefix="factoryops-smoke-") as temporary:
        paths = create_demo(Path(temporary) / "fixture")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=paths.builder,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        print(
            json.dumps(
                {
                    "nonroot": True,
                    "fixture_tests_exit": result.returncode,
                    "live_inference": False,
                    "switch_communication": False,
                },
                sort_keys=True,
            )
        )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
