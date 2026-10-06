"""Unit tests for seat execution runner (run_seat.py)."""

from __future__ import annotations

import asyncio
import io
import os
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch

from factory.run_seat import (
    die,
    extract_mandate_model,
    main,
    mandates_dir,
    read_mandate,
    run,
    usage,
)

FACTORY_ROOT = Path(__file__).resolve().parent.parent


class RunSeatUnitTests(unittest.TestCase):
    def test_die_raises_systemexit(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            die("fatal error", 42)
        self.assertEqual(ctx.exception.code, 42)
        self.assertIn("fatal error", err.getvalue())

    def test_usage_raises_systemexit(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as ctx:
            usage()
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("Usage:", out.getvalue())

    def test_mandates_dir_locates_mandates(self) -> None:
        md = mandates_dir()
        self.assertTrue(md.is_dir())
        self.assertEqual(md.name, "mandates")

    def test_read_mandate_returns_content(self) -> None:
        for seat in ("foreman", "smith", "inspector", "stresser"):
            text = read_mandate(seat)
            self.assertIn("Harness: OpenCode", text)

    def test_read_mandate_nonexistent_fails(self) -> None:
        with self.assertRaises(SystemExit):
            read_mandate("invalid_seat_name")

    def test_extract_mandate_model(self) -> None:
        self.assertEqual(extract_mandate_model("Model: foo/bar\n"), "foo/bar")
        self.assertEqual(extract_mandate_model("**Model**: `baz/qux`\n"), "baz/qux")
        self.assertEqual(extract_mandate_model("- Model: org/test-1\n"), "org/test-1")
        self.assertIsNone(extract_mandate_model("No model declared\n"))


class RunSeatExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.repo_dir = Path(self.tmp_dir.name) / "repo"
        self.repo_dir.mkdir()
        subprocess.run(["git", "-C", str(self.repo_dir), "init", "-b", "main"], check=True, capture_output=True)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_run_missing_result_repo(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                asyncio.run(run("foreman", None))

    def test_run_nonexistent_result_repo(self) -> None:
        with patch.dict(os.environ, {"RESULT_REPO": "/nonexistent/repo"}):
            with self.assertRaises(SystemExit):
                asyncio.run(run("foreman", None))

    def test_run_nongit_result_repo(self) -> None:
        non_git = Path(self.tmp_dir.name) / "nongit"
        non_git.mkdir()
        with patch.dict(os.environ, {"RESULT_REPO": str(non_git)}):
            with self.assertRaises(SystemExit):
                asyncio.run(run("foreman", None))

    def test_run_model_mismatch_fails(self) -> None:
        with patch.dict(os.environ, {"RESULT_REPO": str(self.repo_dir)}):
            with self.assertRaises(SystemExit):
                asyncio.run(run("foreman", "wrong-model-id"))

    @patch("band.Agent.create")
    def test_run_successful_isolated_credentials(self, mock_agent_create: MagicMock) -> None:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=None)
        mock_agent_create.return_value = mock_agent

        env = {
            "RESULT_REPO": str(self.repo_dir),
            "BAND_AGENT_ID": "agent_test_123",
            "BAND_API_KEY": "key_test_456",
            "OPENCODE_SERVER_PASSWORD": "server_auth_secret",
            "OPENCODE_BASE_URL": "http://127.0.0.1:4096",
        }

        with patch.dict(os.environ, env):
            out = io.StringIO()
            with redirect_stdout(out):
                asyncio.run(run("foreman", None))

        mock_agent_create.assert_called_once()
        _, kwargs = mock_agent_create.call_args
        self.assertEqual(kwargs["agent_id"], "agent_test_123")
        self.assertEqual(kwargs["api_key"], "key_test_456")

        # Verify adapter client factory attached basic auth
        adapter = kwargs["adapter"]
        self.assertIsNotNone(adapter._client_factory)
        client = adapter._client_factory(adapter.config)
        self.assertIn("Authorization", client._client.headers)
        self.assertTrue(client._client.headers["Authorization"].startswith("Basic "))

    def test_run_invalid_base_url_fails(self) -> None:
        env = {
            "RESULT_REPO": str(self.repo_dir),
            "BAND_AGENT_ID": "agent_test",
            "BAND_API_KEY": "key_test",
            "OPENCODE_BASE_URL": "ftp://invalid-url:4096",
        }
        with patch.dict(os.environ, env):
            with self.assertRaises(SystemExit):
                asyncio.run(run("foreman", None))

    def test_run_invalid_turn_timeout_fails(self) -> None:
        for bad_timeout in ("not-a-number", "-10", "0"):
            env = {
                "RESULT_REPO": str(self.repo_dir),
                "BAND_AGENT_ID": "agent_test",
                "BAND_API_KEY": "key_test",
                "TURN_TIMEOUT_S": bad_timeout,
            }
            with patch.dict(os.environ, env):
                with self.assertRaises(SystemExit):
                    asyncio.run(run("foreman", None))


class RunSeatCLITests(unittest.TestCase):
    def test_cli_help(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out), patch("sys.argv", ["run_seat.py", "--help"]):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 0)

    def test_cli_model_of(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out), patch("sys.argv", ["run_seat.py", "--model-of", "foreman"]):
            main()
        self.assertIn("zai-org/GLM-5.3-Flash", out.getvalue())

    def test_cli_model_of_invalid_args(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err), patch("sys.argv", ["run_seat.py", "--model-of"]):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertNotEqual(ctx.exception.code, 0)

    def test_cli_invalid_arg_count(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err), patch("sys.argv", ["run_seat.py", "seat1", "model1", "extra_arg"]):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 1)

    @patch("factory.run_seat.run", side_effect=KeyboardInterrupt)
    def test_cli_keyboard_interrupt_clean_exit(self, mock_run: MagicMock) -> None:
        out = io.StringIO()
        with redirect_stdout(out), patch("sys.argv", ["run_seat.py", "foreman"]):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 0)
        self.assertIn("stopped cleanly", out.getvalue())

    @patch("factory.run_seat.run", side_effect=ConnectionError("Server unreachable"))
    def test_cli_connection_error_handling(self, mock_run: MagicMock) -> None:
        err = io.StringIO()
        with redirect_stderr(err), patch("sys.argv", ["run_seat.py", "foreman"]):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 1)
        self.assertIn("failed to connect to OpenCode server or Band platform", err.getvalue())

    @patch("factory.run_seat.run", side_effect=TimeoutError("Turn timeout expired"))
    def test_cli_timeout_error_handling(self, mock_run: MagicMock) -> None:
        err = io.StringIO()
        with redirect_stderr(err), patch("sys.argv", ["run_seat.py", "foreman"]):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 1)
        self.assertIn("timed out during execution", err.getvalue())

    @patch("factory.run_seat.run", side_effect=RuntimeError("Test crash"))
    def test_cli_unhandled_exception(self, mock_run: MagicMock) -> None:
        err = io.StringIO()
        with redirect_stderr(err), patch("sys.argv", ["run_seat.py", "foreman"]):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Test crash", err.getvalue())


if __name__ == "__main__":
    unittest.main()
