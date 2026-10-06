"""Unit tests for BAND room session analyzer (analyze_room.py)."""

from __future__ import annotations

import io
import json
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from factory.analyze_room import (
    _s,
    first,
    fmt,
    main,
    messages,
    parse_time,
    walk,
)


class AnalyzeRoomUnitTests(unittest.TestCase):
    def test_s_extractor(self) -> None:
        self.assertEqual(_s("plain string"), "plain string")
        self.assertEqual(_s({"text": "nested text"}), "nested text")
        self.assertEqual(_s({"name": "display name"}), "display name")
        self.assertIsNone(_s(12345))

    def test_first_lookup(self) -> None:
        d = {"body": "hello", "extra": "world"}
        self.assertEqual(first(d, ("missing", "body")), "hello")
        self.assertIsNone(first(d, ("not_found",)))

    def test_parse_time_formats(self) -> None:
        self.assertIsNone(parse_time(None))
        self.assertIsNone(parse_time("invalid-date-string"))

        # Unix timestamp in seconds
        dt_s = parse_time(1700000000)
        self.assertIsNotNone(dt_s)
        assert dt_s is not None
        self.assertEqual(dt_s.tzinfo, UTC)

        # Unix timestamp in milliseconds
        dt_ms = parse_time(1700000000000)
        self.assertIsNotNone(dt_ms)

        # ISO string with Z
        dt_iso = parse_time("2026-10-06T12:00:00Z")
        self.assertIsNotNone(dt_iso)
        assert dt_iso is not None
        self.assertEqual(dt_iso.year, 2026)

    def test_fmt_timedelta(self) -> None:
        td = timedelta(hours=2, minutes=35, seconds=10)
        self.assertEqual(fmt(td), "2h35m")

    def test_walk_nested_structures(self) -> None:
        data = {"a": [1, {"b": 2}], "c": {"d": 3}}
        elements = list(walk(data))
        self.assertTrue(any(isinstance(e, dict) and "b" in e for e in elements))

    def test_messages_dedup_and_sort(self) -> None:
        raw = [
            {"id": "msg-2", "timestamp": "2026-10-06T10:05:00Z", "sender_name": "Smith", "content": "Building auth"},
            {"id": "msg-1", "timestamp": "2026-10-06T10:00:00Z", "sender_name": "Foreman", "content": "Starting run"},
            # Duplicate msg-1
            {"id": "msg-1", "timestamp": "2026-10-06T10:00:00Z", "sender_name": "Foreman", "content": "Starting run"},
        ]
        parsed = messages(raw)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["sender"], "Foreman")
        self.assertEqual(parsed[1]["sender"], "Smith")


class AnalyzeRoomCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture_data = [
            {
                "id": "1",
                "timestamp": "2026-10-06T09:00:00Z",
                "sender_name": "Operator",
                "role": "user",
                "text": "Dispatch: Implement user authentication and audit for vulnerabilities.",
            },
            {
                "id": "2",
                "timestamp": "2026-10-06T09:01:00Z",
                "sender_name": "Foreman",
                "role": "agent",
                "text": "Planning requirements. @Smith please implement REQ-1.",
            },
            {
                "id": "3",
                "timestamp": "2026-10-06T09:05:00Z",
                "sender_name": "Smith",
                "role": "agent",
                "text": "Committed revision abc1234. @Inspector please audit.",
            },
            {
                "id": "4",
                "timestamp": "2026-10-06T09:10:00Z",
                "sender_name": "Inspector",
                "role": "agent",
                "text": "REJECT: SQL injection vulnerability detected in auth query.",
            },
            {
                "id": "5",
                "timestamp": "2026-10-06T09:15:00Z",
                "sender_name": "Smith",
                "role": "agent",
                "text": "Fixed vulnerability in revision def5678. @Stresser please fuzz.",
            },
            {
                "id": "6",
                "timestamp": "2026-10-06T09:20:00Z",
                "sender_name": "Stresser",
                "role": "agent",
                "text": "Dynamic tests pass across 100 concurrency rounds. Zero defects.",
            },
            {
                "id": "7",
                "timestamp": "2026-10-06T09:25:00Z",
                "sender_name": "Foreman",
                "role": "agent",
                "text": "FINAL REPORT: Mission completed. Revision def5678 accepted.",
            },
        ]

    def test_cli_full_report_with_git_repo(self) -> None:
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            room_json = tmppath / "room.json"
            room_json.write_text(json.dumps(self.fixture_data), encoding="utf-8")

            # Setup git repository for repo commit analysis
            repo_dir = tmppath / "result_repo"
            repo_dir.mkdir()
            subprocess.run(["git", "-C", str(repo_dir), "init", "-b", "main"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Smith"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "smith@factory.invalid"], check=True)
            (repo_dir / "app.py").write_text("print('hello')\n")
            subprocess.run(["git", "-C", str(repo_dir), "add", "app.py"], check=True)
            subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", "feat: initial commit"], check=True)

            out = io.StringIO()
            with redirect_stdout(out), patch("sys.argv", ["analyze_room.py", str(room_json), "--repo", str(repo_dir)]):
                code = main()

            self.assertEqual(code, 0)
            output = out.getvalue()
            self.assertIn("Band Room Session Summary", output)
            self.assertIn("Total messages: 7", output)
            self.assertIn("Messages per sender", output)
            self.assertIn("Operator dispatches: 1", output)
            self.assertIn("Inter-Seat Mention Flow", output)
            self.assertIn("Quality / Resilience Interventions", output)
            self.assertIn("Foreman Final Reports: 1", output)
            self.assertIn("Git Commits per Author", output)
            self.assertIn("Smith: 1", output)

    def test_cli_missing_file_error(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err), patch("sys.argv", ["analyze_room.py", "/nonexistent/room.json"]):
            code = main()
        self.assertEqual(code, 1)
        self.assertIn("File not found", err.getvalue())

    def test_cli_empty_or_unrecognized_json(self) -> None:
        with TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "empty.json"
            p.write_text(json.dumps({"some_key": 123}), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out), patch("sys.argv", ["analyze_room.py", str(p)]):
                code = main()
            self.assertEqual(code, 2)
            self.assertIn("No message records recognized", out.getvalue())


if __name__ == "__main__":
    unittest.main()
