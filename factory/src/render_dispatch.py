#!/usr/bin/env python3
"""
render_dispatch.py — render a dispatch template into the exact message to paste
into the lead seat's room. One source of truth for paths: the dispatch can no
longer point the seats at a different repo than the one the seats run in.

Usage:
    python src/render_dispatch.py pocketful|toy [--stages N]  > message.md

Variables (env, or .env in the factory root):
    RESULT_REPO   required, absolute path of the result repo
    WORK_ROOT     default: parent of the factory dir
    HARNESS_REPO  default: $WORK_ROOT/dark-factory-wearedevs
    CHECKS_DIR    default: $WORK_ROOT/checks

--stages N keeps stage blocks 1..N (e.g. 2 when time is short).
Fails if any {{TOKEN}} is left unresolved.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            m = re.match(r"\s*(?:export\s+)?([A-Za-z_]\w*)\s*=\s*(.*)\s*$", line)
            if m and m.group(1) not in os.environ:
                os.environ[m.group(1)] = m.group(2).strip().strip("'\"")


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help") or args[0] not in ("pocketful", "toy"):
        print(__doc__)
        return 0 if args and args[0] in ("-h", "--help") else 1
    track, stages = args[0], 4
    if "--stages" in args:
        stages = int(args[args.index("--stages") + 1])
    load_env()
    result = os.environ.get("RESULT_REPO", "")
    if not result or not os.path.isabs(result):
        print("ERROR: RESULT_REPO must be set to an absolute path.", file=sys.stderr)
        return 1
    work = os.environ.get("WORK_ROOT") or str(ROOT.parent)
    vals = {
        "RESULT_REPO": result.rstrip("/"),
        "WORK_ROOT": work.rstrip("/"),
        "HARNESS_REPO": (os.environ.get("HARNESS_REPO") or f"{work}/dark-factory-wearedevs").rstrip("/"),
        "CHECKS_DIR": (os.environ.get("CHECKS_DIR") or f"{work}/checks").rstrip("/"),
    }
    text = (ROOT / "dispatch" / f"{track}-all-stages.md").read_text(encoding="utf-8")

    def drop(m: "re.Match[str]") -> str:
        return m.group(0) if int(m.group(1)) <= stages else ""

    text = re.sub(r"<!--stage:(\d+)-->.*?<!--/stage:\1-->\n?", drop, text, flags=re.S)
    text = re.sub(r"^<!--/?stage:\d+-->\n", "", text, flags=re.M)
    for k, v in vals.items():
        text = text.replace("{{" + k + "}}", v)
    left = sorted(set(re.findall(r"\{\{\w+\}\}", text)))
    if left:
        print(f"ERROR: unresolved tokens: {left}", file=sys.stderr)
        return 1
    text = re.sub(r"\n{3,}", "\n\n", text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
