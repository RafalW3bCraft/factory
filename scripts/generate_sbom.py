#!/usr/bin/env python3
"""generate_sbom.py — Generate a CycloneDX v1.5 JSON SBOM from uv.lock.

Usage:
    python scripts/generate_sbom.py [output_path]
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FACTORY_ROOT = Path(__file__).resolve().parent.parent


def parse_uv_lock(lock_path: Path) -> list[dict[str, Any]]:
    """Parse packages from uv.lock file."""
    import tomllib

    content = lock_path.read_bytes()
    data = tomllib.loads(content.decode("utf-8"))
    return data.get("package", [])


def build_cyclonedx_sbom(packages: list[dict[str, Any]]) -> dict[str, Any]:
    """Construct CycloneDX 1.5 JSON SBOM structure."""
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    components: list[dict[str, Any]] = []
    for pkg in packages:
        name = pkg.get("name", "")
        version = pkg.get("version", "")
        if not name or not version:
            continue

        comp: dict[str, Any] = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name}@{version}",
        }

        # Extract sha256 hash if available from sdist or wheels
        sdist = pkg.get("sdist")
        if isinstance(sdist, dict) and "hash" in sdist:
            h = sdist["hash"]
            if h.startswith("sha256:"):
                comp["hashes"] = [{"alg": "SHA-256", "content": h[7:]}]

        components.append(comp)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:7c9e6679-2423-4c96-9811-darkfactory030",
        "version": 1,
        "metadata": {
            "timestamp": now_iso,
            "tools": [{"vendor": "RafalW3bCraft", "name": "dark-factory-sbom-gen", "version": "0.3.0"}],
            "component": {
                "type": "application",
                "name": "dark-factory",
                "version": "0.3.0",
                "licenses": [{"license": {"id": "MIT"}}],
            },
        },
        "components": sorted(components, key=lambda c: c["name"]),
    }


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else FACTORY_ROOT / "sbom.cyclonedx.json"
    lock_path = FACTORY_ROOT / "uv.lock"
    if not lock_path.is_file():
        print(f"ERROR: uv.lock not found at {lock_path}", file=sys.stderr)
        sys.exit(1)

    packages = parse_uv_lock(lock_path)
    sbom = build_cyclonedx_sbom(packages)
    output_path.write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
    print(f"Generated CycloneDX SBOM ({len(sbom['components'])} components) -> {output_path}")


if __name__ == "__main__":
    main()
