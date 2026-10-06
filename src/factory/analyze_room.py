#!/usr/bin/env python3
"""analyze_room.py — Summarize a BAND room session export (room.json).

Reports:
  - Total messages, timestamps, and active duration.
  - Message distribution across seats (@Foreman, @Smith, @Inspector, @Stresser) and human dispatches.
  - Inter-agent mention network (who @-addressed whom).
  - Quality and defect detection events (heuristic) from Inspector and Stresser.
  - Final reports from Foreman.
  - Git repository commit distribution and touched paths (when --repo is provided).

Usage:
    python -m factory.analyze_room room.json [--repo RESULT_REPO] [--seats Foreman,Smith,Inspector,Stresser]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

TEXT_KEYS = ("content", "text", "body", "message", "parts", "blocks")
TIME_KEYS = ("created_at", "inserted_at", "timestamp", "sent_at", "createdAt", "insertedAt", "time", "ts")
SENDER_KEYS = ("sender_name", "sender", "author", "from", "agent_name", "user", "name")
TYPE_KEYS = ("sender_type", "senderType", "author_type", "role")
REJECT = re.compile(
    r"\b(reject(?:ed|ion)?|not accepted|defect|fail(?:ed|s|ure)?|blocked|regression|vulnerability)\b",
    re.I,
)


def _s(v: object) -> str | None:
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        parts = []
        for item in v:
            part_str = _s(item)
            if part_str:
                parts.append(part_str)
        return "\n".join(parts) if parts else None
    if isinstance(v, dict):
        for k in ("text", "content", "name", "display_name", "handle", "username", "id"):
            val = v.get(k)
            extracted = _s(val)
            if extracted:
                return extracted
    return None


def first(d: dict[str, Any], keys: tuple[str, ...]) -> str | None:
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
        raw = str(v).strip()
        if not raw:
            return None
        if raw.replace(".", "", 1).isdigit():
            num = float(raw)
            return datetime.fromtimestamp(num / 1000 if num > 1e11 else num, tz=UTC)
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


def walk(o: object, max_depth: int = 50) -> Generator[Any, None, None]:
    stack: list[tuple[object, int]] = [(o, 0)]
    visited_ids: set[int] = set()
    while stack:
        curr, depth = stack.pop()
        if depth > max_depth:
            continue
        obj_id = id(curr)
        if obj_id in visited_ids:
            continue
        if isinstance(curr, (dict, list)):
            visited_ids.add(obj_id)
        if isinstance(curr, dict):
            yield curr
            for v in curr.values():
                if isinstance(v, (dict, list)):
                    stack.append((v, depth + 1))
        elif isinstance(curr, list):
            for v in curr:
                if isinstance(v, (dict, list)):
                    stack.append((v, depth + 1))


def messages(data: object) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
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
        out.append(
            {
                "ts": ts,
                "sender": sender,
                "text": text,
                "type": (first(merged, TYPE_KEYS) or "").lower(),
            }
        )
    return sorted(out, key=lambda m: m["ts"])


def fmt(td: timedelta) -> str:
    s = int(td.total_seconds())
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a BAND room session export (room.json)")
    parser.add_argument("room_json", help="Path to room.json export file")
    parser.add_argument("--repo", default=None, help="Path to git result repository to analyze commits")
    parser.add_argument(
        "--seats",
        default="Foreman,Smith,Inspector,Stresser",
        help="Comma-separated seat names (default: Foreman,Smith,Inspector,Stresser)",
    )

    args = parser.parse_args()

    seats = [s.strip() for s in args.seats.split(",") if s.strip()]
    json_path = Path(args.room_json)
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

    print(
        f"# Band Room Session Summary\n\nTotal messages: {len(ms)} | Span: {ms[0]['ts']:%Y-%m-%d %H:%M}Z → {ms[-1]['ts']:%Y-%m-%d %H:%M}Z ({fmt(ms[-1]['ts'] - ms[0]['ts'])})"
    )

    per = Counter(m["sender"] for m in ms)
    print("\n## Messages per sender")
    for name, count in per.most_common():
        print(f"- {name}: {count}{'' if isseat(name) else ' (human/operator)'}")

    humans = [m for m in ms if not isseat(m["sender"]) and (m["type"] in ("user", "human", "person") or not m["type"])]
    print(f"\n## Operator dispatches: {len(humans)}")
    for m in humans[:10]:
        print(f"- {m['ts']:%m-%d %H:%M} {m['sender']}: {m['text'][:100]!r}")

    print("\n## Inter-Seat Mention Flow (@mentions)")
    mat: dict[str, Counter[str]] = defaultdict(Counter)
    for m in ms:
        if isseat(m["sender"]):
            for t in re.findall(r"@(\w+)", m["text"]):
                if isseat(t) and t.lower() != m["sender"].lower():
                    mat[m["sender"]][t] += 1
    for s_name, mention_counter in sorted(mat.items()):
        print(f"- {s_name} → " + ", ".join(f"{t}×{n}" for t, n in mention_counter.most_common()))

    rej = [m for m in ms if m["sender"].lower() in ("inspector", "stresser") and REJECT.search(m["text"])]
    print(f"\n## Quality / Resilience Interventions (Inspector & Stresser, heuristic): {len(rej)}")
    for m in rej[:20]:
        print(f"- {m['ts']:%m-%d %H:%M} {m['sender']}: {m['text'][:140].replace(chr(10), ' ')!r}")

    fr = [m for m in ms if m["sender"].lower() == "foreman" and re.search(r"final report", m["text"], re.I)]
    print(f"\n## Foreman Final Reports: {len(fr)}")
    t0 = ms[0]["ts"]
    prev = t0
    for i, m in enumerate(fr, 1):
        print(f"- Report {i} at {m['ts']:%m-%d %H:%M}Z (+{fmt(m['ts'] - prev)} since prev, +{fmt(m['ts'] - t0)} total)")
        prev = m["ts"]

    repo = args.repo
    if repo and Path(repo).is_dir():
        out = subprocess.run(
            ["git", "-C", repo, "log", "--format=%an", "--no-merges"],
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        print("\n## Git Commits per Author")
        for author_name, commit_count in Counter(out).most_common():
            print(f"- {author_name}: {commit_count}")

        files = subprocess.run(
            ["git", "-C", repo, "log", "--format=@@%an", "--name-only", "--no-merges"],
            capture_output=True,
            text=True,
        ).stdout
        dir_touches: dict[str, Counter[str]] = defaultdict(Counter)
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
