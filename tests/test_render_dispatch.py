"""Unit tests for dispatch rendering engine."""

from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from factory.render_dispatch import main, render, resolve_template_path

FACTORY_ROOT = Path(__file__).resolve().parent.parent


class RenderDispatchTests(unittest.TestCase):
    def test_resolve_template_aliases(self) -> None:
        for alias in (
            "engineering",
            "software-engineering",
            "security",
            "security-audit",
            "forensics",
            "forensics-crash",
        ):
            p = resolve_template_path(alias)
            self.assertTrue(p.is_file(), f"Alias {alias} did not resolve to existing template")

    def test_resolve_template_direct_path(self) -> None:
        tmpl = FACTORY_ROOT / "dispatch" / "software-engineering.md.tmpl"
        resolved = resolve_template_path(str(tmpl))
        self.assertEqual(resolved, tmpl)

    def test_resolve_template_missing_raises_filenotfound(self) -> None:
        with self.assertRaises(FileNotFoundError):
            resolve_template_path("nonexistent-template-name")

    def test_render_successful_substitution(self) -> None:
        with TemporaryDirectory() as tmpdir:
            tmpl = Path(tmpdir) / "test.md.tmpl"
            tmpl.write_text("Mission: {{TASK_DESCRIPTION}}\nTarget: {{RESULT_REPO}}\n", encoding="utf-8")

            res = render(tmpl, {"TASK_DESCRIPTION": "Fix critical bug", "RESULT_REPO": "/tmp/repo"})
            self.assertEqual(res, "Mission: Fix critical bug\nTarget: /tmp/repo\n")

    def test_render_unresolved_tokens_raises_valueerror(self) -> None:
        with TemporaryDirectory() as tmpdir:
            tmpl = Path(tmpdir) / "test.md.tmpl"
            tmpl.write_text("Hello {{NAME}}, your role is {{ROLE}} and {{MISSING}}", encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                render(tmpl, {"NAME": "Alice", "ROLE": "Foreman"})
            self.assertIn("MISSING", str(ctx.exception))

    def test_cli_main_success(self) -> None:
        with TemporaryDirectory() as tmpdir:
            out = io.StringIO()
            with (
                redirect_stdout(out),
                patch("sys.argv", ["render_dispatch.py", "engineering", "--repo", tmpdir, "--task", "Build auth API"]),
            ):
                code = main()
            self.assertEqual(code, 0)
            rendered = out.getvalue()
            self.assertIn("Build auth API", rendered)
            self.assertIn(tmpdir, rendered)

    def test_cli_main_missing_repo_error(self) -> None:
        # Clear RESULT_REPO from environment and prevent loading local .env
        with patch.dict(os.environ, {}, clear=True), patch("factory.render_dispatch.load_env_safe"):
            err = io.StringIO()
            with redirect_stderr(err), patch("sys.argv", ["render_dispatch.py", "engineering"]):
                code = main()
            self.assertEqual(code, 1)
            self.assertIn("RESULT_REPO must be provided", err.getvalue())

    def test_cli_main_template_error(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err), patch("sys.argv", ["render_dispatch.py", "unknown-tmpl", "--repo", "/tmp"]):
            code = main()
        self.assertEqual(code, 1)
        self.assertIn("ERROR: Template not found", err.getvalue())


if __name__ == "__main__":
    unittest.main()
