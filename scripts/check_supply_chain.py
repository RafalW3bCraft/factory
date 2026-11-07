"""Check package/version parity across the lock, exported requirements and SBOM."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    expected = {p["name"]: p["version"] for p in lock["package"] if p["name"] != "factory"}
    exported = {}
    for line in (ROOT / "requirements.lock").read_text().splitlines():
        match = re.match(r"^([a-zA-Z0-9_.-]+)(?:\[[^]]+\])?==([^ ;\\]+)", line)
        if match:
            exported[match[1].lower().replace("_", "-")] = match[2]
    sbom = json.loads((ROOT / "sbom.cyclonedx.json").read_text())
    UUID(sbom["serialNumber"].removeprefix("urn:uuid:"))
    components = {c["name"]: c["version"] for c in sbom["components"] if c["name"] != "factory"}
    if expected != exported or expected != components:
        print("FAIL: lock/export/SBOM package versions differ")
        return 1
    print(f"PASS: {len(expected)} locked dependency versions match export and SBOM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
