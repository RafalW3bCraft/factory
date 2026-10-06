#!/usr/bin/env python3
"""Mandate integrity and header test suite."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

FACTORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FACTORY_ROOT / "src"))

from lint_mandates import lint  # noqa: E402
from run_seat import extract_mandate_model  # noqa: E402

MANDATES_DIR = FACTORY_ROOT / "mandates"
EXPECTED_MODELS = {
    "foreman.md": "zai-org/GLM-5.3-Flash",
    "smith.md": "zai-org/GLM-5.3-Flash",
    "inspector.md": "MiniMaxAI/MiniMax-M2.5",
    "stresser.md": "zai-org/GLM-5.3-Flash",
}


class ExtractMandateModelTests(unittest.TestCase):
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


class LiveMandatesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(MANDATES_DIR.is_dir(), f"mandates/ not found at {MANDATES_DIR}")

    def test_all_mandate_files_exist(self) -> None:
        for filename in EXPECTED_MODELS:
            target = MANDATES_DIR / filename
            self.assertTrue(target.is_file(), f"Expected mandate file missing: {filename}")

    def test_all_mandates_have_valid_harness_lines(self) -> None:
        for md in sorted(MANDATES_DIR.glob("*.md")):
            text = md.read_text(encoding="utf-8")
            has_harness = any(
                re.match(r"^[-*_ \t]*Harness[*_ \t]*:\s*OpenCode", line.strip(), re.I)
                for line in text.splitlines()
            )
            self.assertTrue(has_harness, f"{md.name} missing valid 'Harness: OpenCode' line")

    def test_all_mandates_have_expected_models(self) -> None:
        for filename, expected_model in EXPECTED_MODELS.items():
            path = MANDATES_DIR / filename
            model = extract_mandate_model(path.read_text(encoding="utf-8"))
            self.assertEqual(model, expected_model, f"Model mismatch in {filename}")

    def test_linter_passes_on_live_mandates(self) -> None:
        self.assertEqual(lint(MANDATES_DIR), 0)


if __name__ == "__main__":
    unittest.main()
