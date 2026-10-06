"""Unit tests for safe environment variable parser (Finding S3)."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from factory.env import load_env_safe, parse_env_content, parse_env_file


class SafeEnvParserTests(unittest.TestCase):
    def test_parse_basic_key_value(self) -> None:
        content = "FOO=bar\nBAZ=qux\n"
        res = parse_env_content(content)
        self.assertEqual(res, {"FOO": "bar", "BAZ": "qux"})

    def test_parse_with_comments_and_blank_lines(self) -> None:
        content = """
        # This is a comment
        KEY_ONE=val1

        # Another comment
        KEY_TWO=val2
        """
        res = parse_env_content(content)
        self.assertEqual(res, {"KEY_ONE": "val1", "KEY_TWO": "val2"})

    def test_parse_with_export_prefix(self) -> None:
        content = "export API_KEY=secret123\nexport PORT=8080\n"
        res = parse_env_content(content)
        self.assertEqual(res, {"API_KEY": "secret123", "PORT": "8080"})

    def test_parse_quotes(self) -> None:
        content = "DOUBLE=\"hello world\"\nSINGLE='single quote val'\n"
        res = parse_env_content(content)
        self.assertEqual(res, {"DOUBLE": "hello world", "SINGLE": "single quote val"})

    def test_parse_inline_comments(self) -> None:
        content = "PORT=4096 # OpenCode port\nTIMEOUT=900\t# Turn timeout\n"
        res = parse_env_content(content)
        self.assertEqual(res, {"PORT": "4096", "TIMEOUT": "900"})

    def test_arbitrary_shell_is_treated_as_literal_data(self) -> None:
        # Dangerous shell payloads must not be evaluated
        content = "MALICIOUS=$(rm -rf /tmp/test)\nSEMICOLON=test; echo hacked\n"
        res = parse_env_content(content)
        self.assertEqual(res["MALICIOUS"], "$(rm -rf /tmp/test)")
        self.assertEqual(res["SEMICOLON"], "test; echo hacked")

    def test_parse_env_file_missing(self) -> None:
        res = parse_env_file("/path/to/nonexistent/file.env")
        self.assertEqual(res, {})

    def test_load_env_safe_into_os_environ(self) -> None:
        with TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("TEST_FACTORY_ENV_VAR=active_test\n", encoding="utf-8")

            # Clean before test
            if "TEST_FACTORY_ENV_VAR" in os.environ:
                del os.environ["TEST_FACTORY_ENV_VAR"]

            loaded = load_env_safe(env_path)
            self.assertEqual(loaded.get("TEST_FACTORY_ENV_VAR"), "active_test")
            self.assertEqual(os.environ.get("TEST_FACTORY_ENV_VAR"), "active_test")

            # Test override=False does not overwrite existing
            env_path.write_text("TEST_FACTORY_ENV_VAR=overwritten\n", encoding="utf-8")
            load_env_safe(env_path, override=False)
            self.assertEqual(os.environ.get("TEST_FACTORY_ENV_VAR"), "active_test")

            # Test override=True overwrites existing
            load_env_safe(env_path, override=True)
            self.assertEqual(os.environ.get("TEST_FACTORY_ENV_VAR"), "overwritten")

            # Cleanup
            if "TEST_FACTORY_ENV_VAR" in os.environ:
                del os.environ["TEST_FACTORY_ENV_VAR"]


if __name__ == "__main__":
    unittest.main()
