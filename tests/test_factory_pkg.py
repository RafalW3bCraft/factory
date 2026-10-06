"""Unit tests for factory package entrypoint and CLI shims."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import analyze_room
import factory
import lint_mandates
import render_dispatch
import run_seat

FACTORY_ROOT = Path(__file__).resolve().parent.parent


class FactoryPackageTests(unittest.TestCase):
    def test_factory_main_smoke_test(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            factory.main()
        self.assertIn("Factory tooling OK", out.getvalue())

    def test_cli_shims_export_expected_callables(self) -> None:
        self.assertTrue(callable(run_seat.main))
        self.assertTrue(callable(run_seat.extract_mandate_model))
        self.assertTrue(callable(run_seat.read_mandate))

        self.assertTrue(callable(lint_mandates.main))
        self.assertTrue(callable(lint_mandates.lint))

        self.assertTrue(callable(render_dispatch.main))
        self.assertTrue(callable(render_dispatch.render))

        self.assertTrue(callable(analyze_room.main))
        self.assertTrue(callable(analyze_room.messages))


if __name__ == "__main__":
    unittest.main()
