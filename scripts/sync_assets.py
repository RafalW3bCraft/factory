"""Synchronize public runtime resources into the distributable package."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    wanted = {}
    for source, collection in (
        (ROOT / "mandates", "mandates"),
        (ROOT / "dispatch", "dispatch"),
        (ROOT / "switch", "switch"),
        (ROOT / ".agents", "ecc"),
    ):
        for path in sorted(source.rglob("*")):
            if path.is_file() and (path.suffix in (".md", ".yaml", ".yml") or path.name.endswith(".md.tmpl")):
                wanted[ROOT / "src/factory/assets" / collection / path.relative_to(source)] = path.read_bytes()
    changed = False
    for target, data in wanted.items():
        if not target.is_file() or target.read_bytes() != data:
            changed = True
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    assets = ROOT / "src/factory/assets"
    if assets.exists():
        for path in assets.rglob("*"):
            if path.is_file() and path not in wanted:
                changed = True
                if not args.check:
                    path.unlink()
    if args.check and changed:
        print("Packaged assets differ; run python scripts/sync_assets.py")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
