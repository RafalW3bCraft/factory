from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

import yaml

FACTORY_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = FACTORY_ROOT / ".agents" / "rules"

VALID_TRIGGERS = {"always_on", "model_decision", "glob", "manual"}
MAX_FILE_BYTES = 24 * 1024  # 24 KB
ALWAYS_ON_TOKEN_BUDGET = 5000  # Target conservative budget (< 20k token limit)


class AntigravityRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(RULES_DIR.is_dir(), f"Rules directory missing: {RULES_DIR}")
        self.rule_files = sorted(RULES_DIR.glob("*.md"))
        self.assertGreater(len(self.rule_files), 0, "No rule files found in .agents/rules")

    def parse_frontmatter(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            self.fail(f"Rule file {path.name} is missing YAML frontmatter opening '---'")
        parts = text.split("---", 2)
        if len(parts) < 3:
            self.fail(f"Rule file {path.name} has malformed YAML frontmatter")
        try:
            data = yaml.safe_load(parts[1]) or {}
            return data
        except yaml.YAMLError as exc:
            self.fail(f"YAML parsing error in {path.name}: {exc}")

    def test_each_rule_has_valid_trigger_and_metadata(self) -> None:
        always_on_char_count = 0

        for rule in self.rule_files:
            size = rule.stat().st_size
            self.assertLessEqual(
                size,
                MAX_FILE_BYTES,
                f"Rule {rule.name} exceeds 24 KB limit ({size} bytes)",
            )

            fm = self.parse_frontmatter(rule)
            trigger = fm.get("trigger")
            self.assertIn(
                trigger,
                VALID_TRIGGERS,
                f"Rule {rule.name} has missing or invalid trigger '{trigger}'",
            )

            if trigger == "glob":
                globs = fm.get("globs")
                self.assertTrue(
                    isinstance(globs, list) and len(globs) > 0,
                    f"Rule {rule.name} with trigger 'glob' requires non-empty 'globs' list",
                )

            elif trigger == "model_decision":
                desc = fm.get("description")
                self.assertTrue(
                    isinstance(desc, str) and len(desc.strip()) > 0,
                    f"Rule {rule.name} with trigger 'model_decision' requires a non-empty 'description'",
                )

            elif trigger == "always_on":
                always_on_char_count += size

        # Rough token estimate: ~4 chars per token
        est_tokens = always_on_char_count / 4
        self.assertLessEqual(
            est_tokens,
            ALWAYS_ON_TOKEN_BUDGET,
            f"Always-on rules token estimate ({est_tokens}) exceeds budget ({ALWAYS_ON_TOKEN_BUDGET})",
        )

    def test_rules_inventory_count_is_within_budget(self) -> None:
        self.assertLessEqual(len(self.rule_files), 12, "Number of rule files exceeds budget of 12")


if __name__ == "__main__":
    unittest.main()
