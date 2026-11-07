"""CLI wiring tests with explicit mocks; these do not prove live Switch operation."""

from __future__ import annotations

import importlib
import io
import json
import subprocess
import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from factory import factoryops


class DiagnosticsTests(unittest.TestCase):
    def diagnostics(self) -> types.ModuleType:
        return importlib.import_module("factory.diagnostics")

    def test_doctor_returns_only_versions_booleans_and_no_auth_output(self) -> None:
        diagnostics = self.diagnostics()

        def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            if command[-2:] == ["login", "status"]:
                return subprocess.CompletedProcess(command, 0, "Logged in: PRIVATE_TOKEN_SENTINEL", "")
            return subprocess.CompletedProcess(command, 0, "tool 1.2.3 PRIVATE_TOKEN_SENTINEL", "")

        with (
            patch.object(diagnostics.shutil, "which", return_value="/trusted/tool"),
            patch.object(diagnostics.subprocess, "run", side_effect=run),
        ):
            result = diagnostics.doctor()
        self.assertTrue(result["codex_authenticated"])
        self.assertEqual(result["tools"]["codex"]["version"], "1.2.3")
        self.assertNotIn("PRIVATE_TOKEN_SENTINEL", json.dumps(result))
        self.assertNotIn("/trusted/tool", json.dumps(result))

    def test_missing_tools_do_not_start_subprocesses(self) -> None:
        diagnostics = self.diagnostics()
        with (
            patch.object(diagnostics.shutil, "which", return_value=None),
            patch.object(diagnostics.subprocess, "run") as run,
        ):
            result = diagnostics.doctor()
        run.assert_not_called()
        self.assertFalse(result["codex_authenticated"])

    def test_external_health_urls_fail_before_network(self) -> None:
        diagnostics = self.diagnostics()
        for url in (
            "https://example.org",
            "http://127.0.0.1.example.org",
            "http://user:secret@127.0.0.1",
            "file:///tmp/health",
        ):
            with self.subTest(url=url), patch.object(diagnostics.http.client, "HTTPConnection") as connection:
                with self.assertRaises(ValueError):
                    diagnostics.doctor(url)
                connection.assert_not_called()

    def test_health_redirect_is_not_followed_or_exposed(self) -> None:
        diagnostics = self.diagnostics()
        response = Mock(status=302)
        connection = Mock()
        connection.getresponse.return_value = response
        with (
            patch.object(diagnostics.shutil, "which", return_value=None),
            patch.object(diagnostics.http.client, "HTTPConnection", return_value=connection) as constructor,
        ):
            result = diagnostics.doctor("http://localhost:8080")
        constructor.assert_called_once()
        self.assertFalse(result["switch_health"]["healthy"])
        connection.request.assert_called_once_with("GET", "/health", headers={"Accept": "application/json"})

    def test_console_version_uses_package_metadata_without_starting_gui(self) -> None:
        diagnostics = self.diagnostics()
        with (
            patch.object(diagnostics.shutil, "which", side_effect=lambda name: "/bin/" + name),
            patch.object(diagnostics, "_run", return_value=subprocess.CompletedProcess([], 0, "0.40.1\n", "")) as run,
        ):
            result = diagnostics.doctor()
        self.assertEqual(result["tools"]["switch-console"]["version"], "0.40.1")
        self.assertNotIn(["/bin/switch-console", "--version"], [call.args[0] for call in run.call_args_list])
        self.assertIn(
            ["/bin/dpkg-query", "--show", "--showformat=${Version}", "switch-console"],
            [call.args[0] for call in run.call_args_list],
        )

    def test_strict_doctor_blocks_missing_setup_but_default_is_informational(self) -> None:
        diagnostics = self.diagnostics()
        with patch.object(diagnostics.shutil, "which", return_value=None), redirect_stdout(io.StringIO()):
            self.assertEqual(factoryops.main(["doctor"]), 0)
            self.assertEqual(factoryops.main(["doctor", "--strict"]), 1)

    def test_doctor_requires_server_login_and_tools_but_not_optional_docker(self) -> None:
        diagnostics = self.diagnostics()
        tools = {name: {"available": name != "docker", "version": None} for name in diagnostics.TOOLS}
        setup = {"tools": tools, "codex_authenticated": True, "switch_health": {"checked": True, "healthy": True}}
        with patch.object(diagnostics, "doctor", return_value=setup), redirect_stdout(io.StringIO()):
            self.assertEqual(factoryops.main(["doctor", "--strict"]), 0)
            self.assertEqual(factoryops.main(["doctor", "--require-live"]), 1)
            for missing in ("codex_authenticated", "switch_health"):
                invalid = {**setup, missing: False if missing == "codex_authenticated" else {"healthy": False}}
                with patch.object(diagnostics, "doctor", return_value=invalid):
                    self.assertEqual(factoryops.main(["doctor", "--strict"]), 1)


class ControllerCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Mock()
        self.store.status.return_value = {"candidate_sha": "a" * 40, "connection": "disconnected", "stream_live": False}
        self.store.read_report.return_value = {"candidate_sha": "a" * 40, "verified": True}
        self.gate = types.ModuleType("factory.switch_gate")
        self.gate.ledger_from_config = Mock(return_value=self.store)  # type: ignore[attr-defined]
        self.gate.serve = Mock()  # type: ignore[attr-defined]

    def invoke(self, arguments: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(sys.modules, {"factory.switch_gate": self.gate}), redirect_stdout(out), redirect_stderr(err):
            result = factoryops.main(arguments)
        return result, out.getvalue(), err.getvalue()

    def test_status_warns_when_observer_is_disconnected(self) -> None:
        result, out, err = self.invoke(["status", "--state", "/private/state", "--config", "/private/config.json"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(out)["connection"], "disconnected")
        self.assertIn("disconnected", err.lower())
        self.gate.ledger_from_config.assert_called_once_with(Path("/private/state"), Path("/private/config.json"))  # type: ignore[attr-defined]

    def test_strict_status_blocks_disconnection_and_unknown_native_readiness(self) -> None:
        arguments = ["status", "--state", "/private/state", "--config", "/private/config.json"]
        self.assertEqual(self.invoke([*arguments, "--strict"])[0], 1)
        self.store.status.return_value = {"stream_live": True}
        self.assertEqual(self.invoke([*arguments, "--strict"])[0], 0)
        self.assertEqual(self.invoke([*arguments, "--require-live"])[0], 1)
        self.store.status.return_value = {"stream_live": True, "required_seats_live": True}
        self.assertEqual(self.invoke([*arguments, "--require-live"])[0], 0)
        self.store.status.return_value = {"stream_live": False, "required_seats_live": True}
        self.assertEqual(self.invoke([*arguments, "--require-live"])[0], 1)

    def test_report_uses_verified_persisted_artifact(self) -> None:
        result, out, _ = self.invoke(["report", "--state", "/private/state", "--config", "/private/config.json"])
        self.assertEqual(result, 0)
        self.assertTrue(json.loads(out)["verified"])
        self.store.read_report.assert_called_once_with()

    def test_gate_starts_only_explicit_controller_adapter(self) -> None:
        result, _, _ = self.invoke(["gate", "--state", "/private/state", "--config", "/private/config.json"])
        self.assertEqual(result, 0)
        self.gate.serve.assert_called_once_with(Path("/private/state"), Path("/private/config.json"))  # type: ignore[attr-defined]

    def test_invalid_image_is_rejected_without_controller_or_container(self) -> None:
        result, _, err = self.invoke(
            [
                "verify",
                "--root",
                "/demo",
                "--role",
                "inspector",
                "--commit",
                "a" * 40,
                "--state",
                "/private/state",
                "--config",
                "/private/config.json",
                "--image",
                "python:latest",
            ]
        )
        self.assertEqual(result, 1)
        self.gate.ledger_from_config.assert_not_called()  # type: ignore[attr-defined]
        self.assertIn("immutable", err)

    def test_controller_exception_does_not_echo_credentials(self) -> None:
        self.gate.ledger_from_config.side_effect = ValueError("PRIVATE_TOKEN_SENTINEL")  # type: ignore[attr-defined]
        result, out, err = self.invoke(["status", "--state", "/private/state", "--config", "/private/config.json"])
        self.assertEqual(result, 1)
        self.assertNotIn("PRIVATE_TOKEN_SENTINEL", out + err)
