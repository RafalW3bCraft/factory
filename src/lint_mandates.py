#!/usr/bin/env python3
"""
lint_mandates.py — fail if any mandate names track-specific detail.

The hackathon disqualifies an entry whose mandate names anything specific to the
track or challenge (endpoint paths, field names, error codes, ...). This is the
mechanical version of "could you hand these mandates to a team building something
completely different?".

Usage: python src/lint_mandates.py [mandates_dir]     (stdlib only)
Exit 0 = clean, 1 = violations (printed as file:line: rule: text).
Heuristic: it can false-positive (fix the wording) but should not miss the
obvious cases. It is a gate, not a substitute for re-reading the mandates.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = re.compile(r"^[-*_ \t]*(Harness|Model)[*_ \t]*:", re.I)

RULES = [
    ("http-verb+path", re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|HEAD)\s+/")),
    ("url-path", re.compile(r"(?<![\w.:/])/[A-Za-z_{][\w\-{}/.]*")),
    ("snake_case-identifier", re.compile(r"\b_?[a-z]+(?:_[a-z0-9]+)+\b")),
    ("camelCase-identifier", re.compile(r"\b[a-z]+[A-Z][a-z]+[A-Za-z]*\b")),
    ("http-status-code", re.compile(r"(?i)\b(?:http|status|code)s?\s*[:=]?\s*[1-5]\d\d\b")),
    ("header-name", re.compile(r"\b[A-Z][a-z]+(?:-[A-Z][a-z]+)+\b")),
    ("track-vocabulary", re.compile(
        r"(?i)\b(pocketful|tablekeeper|wallets?|payments?|money|balances?|refunds?|"
        r"ledgers?|transfers?|settlements?|currency|cents|reservations?|bookings?|"
        r"restaurants?|venmo|opentable|diners?|covers)\b")),
]


def lint(dirpath: Path) -> int:
    files = sorted(dirpath.glob("*.md"))
    if not files:
        print(f"lint_mandates: no mandates in {dirpath}", file=sys.stderr)
        return 1
    bad = 0
    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if HEADER.match(line):
                continue
            for name, rx in RULES:
                m = rx.search(line)
                if m:
                    bad += 1
                    print(f"{f.name}:{n}: {name}: {m.group(0)!r}  |  {line.strip()}")
    print(f"lint_mandates: {len(files)} mandates, {bad} violation(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else next(
        (c for c in (ROOT / "mandates", ROOT.parent / "mandates") if c.is_dir()), ROOT / "mandates")
    sys.exit(lint(d))
