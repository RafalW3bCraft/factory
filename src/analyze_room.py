#!/usr/bin/env python3
"""
analyze_room.py — Summarize a BAND room session export (room.json).

Reports:
  - Total messages, timestamps, and active duration.
  - Message distribution across seats (@Foreman, @Smith, @Inspector, @Stresser) and human dispatches.
  - Inter-agent mention network (who @-addressed whom).
  - Rejection and defect detection events from Inspector and Stresser.
  - Final reports from Foreman.
  - Git repository commit distribution and touched paths (when --repo is provided).

Usage:
    python src/analyze_room.py room.json [--repo RESULT_REPO] [--seats Foreman,Smith,Inspector,Stresser]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

TEXT_KEYS = ("content", "text", "body", "message")
TIME_KEYS = ("created_at", "inserted_at", "timestamp", "sent_at", "createdAt", "insertedAt", "time", "ts")
SENDER_KEYS = ("sender_name", "sender", "author", "from", "agent_name", "user", "name")
TYPE_KEYS = ("sender_type", "senderType", "author_type", "role")
REJECT = re.compile(r"\b(reject(?:ed|ion)?|not accepted|defect|fail(?:ed|s|ure)?|blocked|regression|vulnerability)\b", re.I)


def _s(v: object) -> str | None:
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in ("text", "content", "name", "display_name", "handle", "username", "id"):
            val = v.get(k)
            if isinstance(val, str):
                return val
    return None


def first(d: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        if k in d and _s(d[k]):
            return _s(d[k])
    return None


def parse_time(v: object) -> datetime | None:
    if v is None:
        return None
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, tz=UTC)
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


def walk(o: object):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def messages(data: object) -> list[dict]:
    out: list[dict] = []
    seen = set()
    for d in walk(data):
        if not isinstance(d, dict):
            continue
        merged = dict(d)
        for k in ("payload", "data", "message", "content"):
            sub = d.get(k)
            if isinstance(sub, dict):
                merged = {**sub, **{kk: vv for kk, vv in d.items() if kk != k}, "content": sub}
        text = first(merged, TEXT_KEYS)
        ts = next((parse_time(merged[k]) for k in TIME_KEYS if k in merged and parse_time(merged[k])), None)
        sender = first(merged, SENDER_KEYS)
        if not (text and ts and sender):
            continue
        key = (merged.get("id"), ts, sender, text[:80])
        if key in seen:
            continue
        seen.add(key)
        out.append({"ts": ts, "sender": sender, "text": text, "type": (first(merged, TYPE_KEYS) or "").lower()})
    return sorted(out, key=lambda m: m["ts"])


def fmt(td) -> str:
    s = int(td.total_seconds())
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    seats = ["Foreman", "Smith", "Inspector", "Stresser"]
    repo = None
    if "--seats" in args:
        seats = args[args.index("--seats") + 1].split(",")
    if "--repo" in args:
        repo = args[args.index("--repo") + 1]

    json_path = Path(args[0])
    if not json_path.is_file():
        print(f"ERROR: File not found: {json_path}", file=sys.stderr)
        return 1

    data = json.loads(json_path.read_text(encoding="utf-8"))
    ms = messages(data)
    if not ms:
        top = list(data.keys()) if isinstance(data, dict) else f"list[{len(data)}]"
        print(f"No message records recognized. Top structure: {top}")
        return 2

    seatset = {s.lower() for s in seats}

    def isseat(name: str) -> bool:
        return name.lower().lstrip("@") in seatset

    print(f"# Band Room Session Summary\n\nTotal messages: {len(ms)} | Span: {ms[0]['ts']:%Y-%m-%d %H:%M}Z → {ms[-1]['ts']:%Y-%m-%d %H:%M}Z ({fmt(ms[-1]['ts'] - ms[0]['ts'])})")

    per = Counter(m["sender"] for m in ms)
    print("\n## Messages per sender")
    for n, c in per.most_common():
        print(f"- {n}: {c}{'' if isseat(n) else ' (human/operator)'}")

    humans = [m for m in ms if not isseat(m["sender"]) and (m["type"] in ("user", "human", "person") or not m["type"])]
    print(f"\n## Operator dispatches: {len(humans)}")
    for m in humans[:10]:
        print(f"- {m['ts']:%m-%d %H:%M} {m['sender']}: {m['text'][:100]!r}")

    print("\n## Inter-Seat Mention Flow (@mentions)")
    mat: dict[str, Counter] = defaultdict(Counter)
    for m in ms:
        if isseat(m["sender"]):
            for t in re.findall(r"@(\w+)", m["text"]):
                if isseat(t) and t.lower() != m["sender"].lower():
                    mat[m["sender"]][t] += 1
    for s, c in sorted(mat.items()):
        print(f"- {s} → " + ", ".join(f"{t}×{n}" for t, n in c.most_common()))

    rej = [m for m in ms if m["sender"].lower() in ("inspector", "stresser") and REJECT.search(m["text"])]
    print(f"\n## Quality / Resilience Interventions (Inspector & Stresser): {len(rej)}")
    for m in rej[:20]:
        print(f"- {m['ts']:%m-%d %H:%M} {m['sender']}: {m['text'][:140].replace(chr(10), ' ')!r}")

    fr = [m for m in ms if m["sender"].lower() == "foreman" and re.search(r"final report", m["text"], re.I)]
    print(f"\n## Foreman Final Reports: {len(fr)}")
    t0 = ms[0]["ts"]
    prev = t0
    for i, m in enumerate(fr, 1):
        print(f"- Report {i} at {m['ts']:%m-%d %H:%M}Z (+{fmt(m['ts'] - prev)} since prev, +{fmt(m['ts'] - t0)} total)")
        prev = m["ts"]

    if repo and Path(repo).is_dir():
        out = subprocess.run(["git", "-C", repo, "log", "--format=%an", "--no-merges"], capture_output=True, text=True).stdout.splitlines()
        print("\n## Git Commits per Author")
        for n, c in Counter(out).most_common():
            print(f"- {n}: {c}")

        files = subprocess.run(["git", "-C", repo, "log", "--format=@@%an", "--name-only", "--no-merges"], capture_output=True, text=True).stdout
        dir_touches: dict[str, Counter] = defaultdict(Counter)
        cur_author = None
        for line in files.splitlines():
            line = line.strip()
            if line.startswith("@@"):
                cur_author = line[2:]
            elif line and cur_author:
                top_part = line.split("/")[0] if "/" in line else "root"
                dir_touches[top_part][cur_author] += 1

        print("## Path Activity by Author")
        for d in sorted(dir_touches):
            print(f"- {d}/: " + ", ".join(f"{n}×{c}" for n, c in dir_touches[d].most_common()))

    return 0


if __name__ == "__main__":
    sys.exit(main())
