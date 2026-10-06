"""Unit tests for mandate linter and secret hygiene scanner."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from factory.lint_mandates import lint, main

FACTORY_ROOT = Path(__file__).resolve().parent.parent


class LintMandatesTests(unittest.TestCase):
    def test_lint_live_mandates_passes(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = lint(FACTORY_ROOT / "mandates")
        self.assertEqual(code, 0)
        self.assertIn("verified successfully", out.getvalue())

    def test_lint_nonexistent_directory_fails(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code = lint(Path("/nonexistent/mandates_dir"))
        self.assertEqual(code, 1)
        self.assertIn("not found", err.getvalue())

    def test_lint_empty_directory_fails(self) -> None:
        with TemporaryDirectory() as tmpdir:
            err = io.StringIO()
            with redirect_stderr(err):
                code = lint(Path(tmpdir))
            self.assertEqual(code, 1)
            self.assertIn("No .md files found", err.getvalue())

    def test_lint_missing_seat_fails(self) -> None:
        with TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            # Create only 3 of 4 seats
            for seat in ("foreman", "smith", "inspector"):
                (d / f"{seat}.md").write_text("Harness: OpenCode\nModel: test/model\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                code = lint(d)
            self.assertEqual(code, 1)
            self.assertIn("Missing required mandate: stresser.md", err.getvalue())

    def test_lint_unsupported_harness_fails(self) -> None:
        with TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            for seat in ("foreman", "smith", "inspector", "stresser"):
                harness = "ClaudeCode" if seat == "smith" else "OpenCode"
                (d / f"{seat}.md").write_text(f"Harness: {harness}\nModel: test/model\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                code = lint(d)
            self.assertEqual(code, 1)
            self.assertIn("Unsupported Harness 'ClaudeCode'", err.getvalue())

    def test_lint_missing_model_fails(self) -> None:
        with TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            for seat in ("foreman", "smith", "inspector", "stresser"):
                model_line = "Model:\n" if seat == "stresser" else "Model: test/model\n"
                (d / f"{seat}.md").write_text(f"Harness: OpenCode\n{model_line}", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                code = lint(d)
            self.assertEqual(code, 1)
            self.assertIn("Missing 'Model: <model_id>' header", err.getvalue())

    def test_lint_detects_secrets(self) -> None:
        secret_payloads = [
            ("api_key_sk", "sk-123456789012345678901234"),
            ("api_key_rc", "rc_abcdefghijklmnopqrstuvwx"),
            ("api_key_ghp", "ghp_123456789012345678901234"),
            ("bearer", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"),
            ("private_key", "-----BEGIN RSA PRIVATE KEY-----"),
            ("password_assign", 'password = "my_super_secret_password"'),
        ]
        for name, payload in secret_payloads:
            with TemporaryDirectory() as tmpdir:
                d = Path(tmpdir)
                for seat in ("foreman", "smith", "inspector", "stresser"):
                    extra = f"\nLeak: {payload}\n" if seat == "foreman" else "\n"
                    (d / f"{seat}.md").write_text(f"Harness: OpenCode\nModel: test/model\n{extra}", encoding="utf-8")
                err = io.StringIO()
                with redirect_stderr(err):
                    code = lint(d)
                self.assertEqual(code, 1, f"Secret detector missed payload: {name}")
                self.assertIn("Potential secret detected", err.getvalue(), f"Error message missing for {name}")

    def test_cli_main_wrapper(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out), patch("sys.argv", ["lint_mandates.py", str(FACTORY_ROOT / "mandates")]):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
