#!/usr/bin/env python3
"""Mandate header tests. Stdlib unittest only: python3 tests/test_mandates.py"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from run_seat import extract_mandate_model  # noqa: E402

ROOT_MANDATES = Path(__file__).resolve().parents[2] / "mandates"


class ExtractMandateModel(unittest.TestCase):
    def test_extract_model_basic(self) -> None:
        text = "# Foreman\n\n**Model:** zai-org/GLM-5.3-Flash\n"
        self.assertEqual(extract_mandate_model(text), "zai-org/GLM-5.3-Flash")

    def test_extract_model_with_dashes(self) -> None:
        text = "- Model: MiniMaxAI/MiniMax-M2.5\n"
        self.assertEqual(extract_mandate_model(text), "MiniMaxAI/MiniMax-M2.5")

    def test_extract_model_missing_returns_none(self) -> None:
        self.assertIsNone(extract_mandate_model("# No model line here\n"))

    def test_extract_model_strips_backticks(self) -> None:
        self.assertEqual(extract_mandate_model("Model: `some/model`\n"), "some/model")

    def test_extract_model_strips_bold(self) -> None:
        self.assertEqual(extract_mandate_model("**Model**: some/model\n"), "some/model")


class LiveMandates(unittest.TestCase):
    def test_all_mandates_have_model_lines(self) -> None:
        self.assertTrue(ROOT_MANDATES.is_dir(), f"mandates/ not found at {ROOT_MANDATES}")
        for md in sorted(ROOT_MANDATES.glob("*.md")):
            model = extract_mandate_model(md.read_text(encoding="utf-8"))
            self.assertIsNotNone(model, f"{md.name} has no 'Model:' line")
            self.assertTrue(model, f"{md.name} 'Model:' line is empty")

    def test_all_mandates_have_harness_lines(self) -> None:
        self.assertTrue(ROOT_MANDATES.is_dir())
        for md in sorted(ROOT_MANDATES.glob("*.md")):
            text = md.read_text(encoding="utf-8")
            has_harness = any(
                re.match(r"^[-*_ \t]*Harness[*_ \t]*:", line.strip())
                for line in text.splitlines()
            )
            self.assertTrue(has_harness, f"{md.name} has no 'Harness:' line")

    def test_inspector_model_is_minimax(self) -> None:
        model = extract_mandate_model((ROOT_MANDATES / "inspector.md").read_text(encoding="utf-8"))
        self.assertEqual(model, "MiniMaxAI/MiniMax-M2.5")


if __name__ == "__main__":
    unittest.main()
