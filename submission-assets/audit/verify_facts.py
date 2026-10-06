#!/usr/bin/env python3
"""Verify the ground-truth facts in room.json against the repo's known evidence."""

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROOM = ROOT / 'room.json'


def iso_to_dt(value: str):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def main():
    with ROOM.open('r', encoding='utf-8') as f:
        data = json.load(f)
    messages = data['messages']
    sender_counts = Counter(m.get('senderName') or 'unknown' for m in messages)
    human = [m for m in messages if (m.get('senderName') or '').strip() == 'Metal']
    timeouts = [m for m in messages if 'OpenCode timed out before completing the turn.' in (m.get('content') or '')]
    first = messages[0]
    last = messages[-1]
    room_start = iso_to_dt(first['insertedAt'])
    room_end = iso_to_dt(last['insertedAt'])
    duration = room_end - room_start

    summary = {
        'room_id': data.get('room', {}).get('id'),
        'room_title': data.get('room', {}).get('title'),
        'total_messages': len(messages),
        'first_message_timestamp': first['insertedAt'],
        'last_message_timestamp': last['insertedAt'],
        'room_duration_seconds': int(duration.total_seconds()),
        'sender_counts': dict(sorted(sender_counts.items())),
        'human_message_count': len(human),
        'human_message_ids': [m['id'] for m in human],
        'timeout_count': len(timeouts),
        'timeout_message_ids': [m['id'] for m in timeouts],
        'timeout_timestamps': [m['insertedAt'] for m in timeouts],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    print('\nHuman messages:')
    for m in human:
        print(f"- {m['id']} | {m['insertedAt']} | {m['content'][:180]}")

    print('\nTimeout events:')
    for m in timeouts:
        print(f"- {m['id']} | {m['insertedAt']} | {m.get('senderName')} | {m.get('content')[:120]}")

    patt = [
        ('dispatch', 'full Stage 1-4 work order'),
        ('re-dispatch', 'Identical re-dispatch'),
        ('continue', 'continue'),
        ('steering note', 'Next: commit to review to probe to Stage 2 report'),
        ('stage1 final', 'Stage 1 FINAL REPORT'),
    ]
    print('\nTarget phrases:')
    for label, text in patt:
        matches = [m for m in messages if text in (m.get('content') or '')]
        print(f"- {label}: {len(matches)}")
        for m in matches[:3]:
            print(f"  {m['id']} | {m['insertedAt']} | {m.get('senderName')}")

    # Specific defect and acceptance markers from FACT_SHEET.md
    marker_text = [
        ('C1 concern', '1 unresolved concern'),
        ('C2 bonus', 'Bonus defect found & fixed'),
        ('Inspector accepted', 'Inspector ACCEPTED'),
        ('delta accepted', 'Delta-ACCEPTED'),
        ('FATAL', 'FATAL opencode server died'),
    ]
    print('\nMarker scan:')
    for label, text in marker_text:
        matches = [m for m in messages if text in (m.get('content') or '')]
        print(f"- {label}: {len(matches)}")
        for m in matches[:5]:
            print(f"  {m['id']} | {m['insertedAt']} | {m.get('senderName')} | {m.get('content')[:120]}")


if __name__ == '__main__':
    main()
