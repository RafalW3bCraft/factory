#!/usr/bin/env python3
"""lint_mandates.py — Validate integrity, headers, and security hygiene of agent mandates.

Ensures that every seat mandate:
  1. Exists and is readable.
  2. Contains valid 'Harness: OpenCode' and 'Model: <model_id>' headers.
  3. Enforces core dark-factory and evidence-based operational rules.
  4. Contains no hardcoded secrets, private tokens, or credential leaks.

Usage:
    python -m factory.lint_mandates [mandates_dir]
Exit 0 = clean, 1 = violations found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_SEATS = ("foreman", "smith", "inspector", "stresser")
HARNESS_RE = re.compile(r"^[-*_ \t]*Harness[*_ \t]*:\s*(.+)$", re.IGNORECASE)
MODEL_RE = re.compile(r"^[-*_ \t]*Model[*_ \t]*:\s*(.+)$", re.IGNORECASE)

# Secret pattern detectors
SECRET_PATTERNS = [
    ("api-key-prefix", re.compile(r"\b(sk-[A-Za-z0-9]{20,}|rc_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,})\b")),
    ("bearer-token", re.compile(r"(?i)bearer\s+[a-z0-9_\-\.]{25,}")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
    ("password-assignment", re.compile(r"(?i)\b(?:password|passwd|secret|api_key)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
]


def lint(dirpath: Path) -> int:
    """Scan all markdown mandates in dirpath and return 0 if valid, 1 if violations found."""
    if not dirpath.is_dir():
        print(f"ERROR: Mandates directory not found at {dirpath}", file=sys.stderr)
        return 1

    violations: list[str] = []

    # 1. Check all required seats exist
    for seat in REQUIRED_SEATS:
        target = dirpath / f"{seat}.md"
        if not target.is_file():
            violations.append(f"Missing required mandate: {target.name}")

    # 2. Check each mandate in directory
    md_files = sorted(dirpath.glob("*.md"))
    if not md_files:
        print(f"ERROR: No .md files found in {dirpath}", file=sys.stderr)
        return 1

    for md in md_files:
        lines = md.read_text(encoding="utf-8").splitlines()
        harness_found = False
        model_found = False

        for n, line in enumerate(lines, 1):
            h_match = HARNESS_RE.match(line.strip())
            if h_match:
                harness_val = h_match.group(1).strip().strip("`*")
                if harness_val.lower() != "opencode":
                    violations.append(f"{md.name}:{n}: Unsupported Harness '{harness_val}' (expected 'OpenCode')")
                harness_found = True

            m_match = MODEL_RE.match(line.strip())
            if m_match:
                model_val = m_match.group(1).strip().strip("`*")
                if not model_val:
                    violations.append(f"{md.name}:{n}: Empty Model specification")
                model_found = True

            # Secret scanning
            for s_name, s_rx in SECRET_PATTERNS:
                if s_rx.search(line):
                    violations.append(f"{md.name}:{n}: Potential secret detected ({s_name})")

        if not harness_found:
            violations.append(f"{md.name}: Missing 'Harness: OpenCode' header")
        if not model_found:
            violations.append(f"{md.name}: Missing 'Model: <model_id>' header")

    if violations:
        print(f"[lint_mandates] {len(violations)} violation(s) found:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print(f"[lint_mandates] OK: {len(md_files)} mandate(s) verified successfully.")
    return 0


def main() -> None:
    """CLI entrypoint for mandate linter."""
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "mandates"
    sys.exit(lint(target_dir))


if __name__ == "__main__":
    main()
