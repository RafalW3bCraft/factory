#!/usr/bin/env python3
"""
analyze_room.py — summarise a BAND room export (room.json) for FACTORY.md, the
video and the slides, and sanity-check the "Agent Teamwork" criteria.

Usage:
    python src/analyze_room.py room.json [--repo RESULT_REPO] [--seats Foreman,Smith,Inspector,Stresser]

Reports: messages per sender, HUMAN messages (autonomy: should equal the number of
dispatches), time span, who @-addressed whom (reciprocity), rejection/defect events
(the "bad work it caught" evidence), "final report" timestamps (stage durations),
and with --repo: commits per author and per stage folder.

The export schema is not documented here, so this is schema-tolerant: it walks the
JSON for message-like records. If it recognises nothing it prints the top-level
structure; paste ~30 lines of the file and the extraction can be adapted.
Stdlib only.
"""
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

TEXT_KEYS = ("content", "text", "body", "message")
TIME_KEYS = ("created_at", "inserted_at", "timestamp", "sent_at", "createdAt", "insertedAt", "time", "ts")
SENDER_KEYS = ("sender_name", "sender", "author", "from", "agent_name", "user", "name")
TYPE_KEYS = ("sender_type", "senderType", "author_type", "role")
REJECT = re.compile(r"\b(reject(?:ed|ion)?|not accepted|defect|fail(?:ed|s|ure)?|blocked|regression)\b", re.I)


def _s(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in ("text", "content", "name", "display_name", "handle", "username", "id"):
            if isinstance(v.get(k), str):
                return v[k]
    return None


def first(d, keys):
    for k in keys:
        if k in d and _s(d[k]):
            return _s(d[k])
    return None


def parse_time(v):
    if v is None:
        return None
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, tz=timezone.utc)
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def messages(data):
    out, seen = [], set()
    for d in walk(data):
        merged = dict(d)
        for k in ("payload", "data", "message", "content"):  # text one level down
            if isinstance(d.get(k), dict):
                merged = {**d[k], **{kk: vv for kk, vv in d.items() if kk != k}, "content": d[k]}
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


def fmt(td):
    s = int(td.total_seconds())
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    seats = ["Foreman", "Smith", "Inspector", "Stresser"]
    repo = None
    if "--seats" in a:
        seats = a[a.index("--seats") + 1].split(",")
    if "--repo" in a:
        repo = a[a.index("--repo") + 1]
    data = json.loads(Path(a[0]).read_text(encoding="utf-8"))
    ms = messages(data)
    if not ms:
        top = list(data.keys()) if isinstance(data, dict) else f"list[{len(data)}]"
        print(f"No message-like records recognised. Top-level structure: {top}")
        print("Paste ~30 lines of the file and this extractor can be adapted.")
        return 2
    seatset = {s.lower() for s in seats}
    isseat = lambda n: n.lower().lstrip("@") in seatset
    print(f"# Room summary\n\nmessages: {len(ms)}   span: {ms[0]['ts']:%Y-%m-%d %H:%M}Z → {ms[-1]['ts']:%Y-%m-%d %H:%M}Z  ({fmt(ms[-1]['ts'] - ms[0]['ts'])})")
    per = Counter(m["sender"] for m in ms)
    print("\n## Messages per sender")
    for n, c in per.most_common():
        print(f"- {n}: {c}{'' if isseat(n) else '   <- not a seat'}")
    humans = [m for m in ms if not isseat(m["sender"]) and (m["type"] in ("user", "human", "person") or not m["type"])]
    print(f"\n## Human / non-seat messages: {len(humans)}  (autonomy: should be exactly your dispatch count)")
    for m in humans[:12]:
        print(f"- {m['ts']:%m-%d %H:%M} {m['sender']}: {m['text'][:110]!r}")
    print("\n## Who addressed whom (@mentions by seats)")
    mat = defaultdict(Counter)
    for m in ms:
        if isseat(m["sender"]):
            for t in re.findall(r"@(\w+)", m["text"]):
                if isseat(t) and t.lower() != m["sender"].lower():
                    mat[m["sender"]][t] += 1
    for s, c in sorted(mat.items()):
        print(f"- {s} → " + ", ".join(f"{t}×{n}" for t, n in c.most_common()))
    pairs = [(x, y) for x in mat for y in mat[x] if x.lower() < y.lower() and mat.get(y, {}).get(x)]
    print("reciprocal pairs: " + (", ".join(f"{x}↔{y}" for x, y in pairs) or "NONE (gate risk!)"))
    rej = [m for m in ms if m["sender"].lower() in ("inspector", "stresser") and REJECT.search(m["text"])]
    print(f"\n## Candidate rejections/defects (Inspector/Stresser; keyword match — verify by reading): {len(rej)}")
    for m in rej[:25]:
        print(f"- {m['ts']:%m-%d %H:%M} {m['sender']}: {m['text'][:150].replace(chr(10), ' ')!r}")
    fr = [m for m in ms if m["sender"].lower() == "foreman" and re.search(r"final report", m["text"], re.I)]
    print(f"\n## Foreman 'final report' messages: {len(fr)}")
    t0 = ms[0]["ts"]
    prev = t0
    for i, m in enumerate(fr, 1):
        print(f"- report {i} at {m['ts']:%m-%d %H:%M}Z  (+{fmt(m['ts'] - prev)} since previous; +{fmt(m['ts'] - t0)} since room start)")
        prev = m["ts"]
    if repo:
        out = subprocess.run(["git", "-C", repo, "log", "--format=%an", "--no-merges"], capture_output=True, text=True).stdout.split()
        print("\n## Commits per author (repo)")
        for n, c in Counter(out).most_common():
            print(f"- {n}: {c}")
        files = subprocess.run(["git", "-C", repo, "log", "--format=@@%an", "--name-only", "--no-merges"], capture_output=True, text=True).stdout
        st, cur = defaultdict(Counter), None
        for line in files.splitlines():
            if line.startswith("@@"):
                cur = line[2:]
            elif line.startswith("stage-") and cur:
                st[line.split("/")[0]][cur] += 1
        print("## File-touches per stage folder × author")
        for k in sorted(st):
            print(f"- {k}: " + ", ".join(f"{n}×{c}" for n, c in st[k].most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
