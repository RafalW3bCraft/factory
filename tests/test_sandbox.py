"""Security and sandbox containment verification tests (Findings S1, S2, S5)."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

FACTORY_ROOT = Path(__file__).resolve().parent.parent


class SandboxSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dockerfile = FACTORY_ROOT / "Dockerfile.sandbox"
        self.compose = FACTORY_ROOT / "docker-compose.sandbox.yml"

    def test_dockerfile_sandbox_exists_and_enforces_non_root(self) -> None:
        self.assertTrue(self.dockerfile.is_file(), "Dockerfile.sandbox missing")
        content = self.dockerfile.read_text(encoding="utf-8")
        # S1: Must run as unprivileged user
        self.assertIn("USER factory", content, "Dockerfile.sandbox must specify non-root USER")
        self.assertIn("useradd", content, "Dockerfile.sandbox must create unprivileged user")
        # Working dir scoped to /workspace
        self.assertIn("WORKDIR /workspace", content)

    def test_compose_sandbox_enforces_containment_and_limits(self) -> None:
        self.assertTrue(self.compose.is_file(), "docker-compose.sandbox.yml missing")
        raw = yaml.safe_load(self.compose.read_text(encoding="utf-8"))

        services = raw.get("services", {})
        self.assertIn("factory-sandbox", services)
        svc = services["factory-sandbox"]

        # S1: Non-root user ID
        self.assertEqual(svc.get("user"), "1000:1000")

        # S1: Restricted mounts — only /workspace is mounted
        volumes = svc.get("volumes", [])
        self.assertTrue(len(volumes) >= 1)
        workspace_mount = False
        for v in volumes:
            if isinstance(v, dict):
                if v.get("target") == "/workspace":
                    workspace_mount = True
                # Ensure no host home or root directory is mounted
                self.assertNotIn("/home", str(v.get("target")))
                self.assertNotIn("/root", str(v.get("target")))
        self.assertTrue(workspace_mount, "/workspace must be configured as mount point")

        # S1: Security containment: drop caps, no-new-privileges
        sec_opts = svc.get("security_opt", [])
        self.assertIn("no-new-privileges:true", sec_opts)

        cap_drops = svc.get("cap_drop", [])
        self.assertIn("ALL", cap_drops)

        # S1: Resource limits configured
        limits = svc.get("deploy", {}).get("resources", {}).get("limits", {})
        self.assertIn("cpus", limits)
        self.assertIn("memory", limits)
        self.assertIn("pids", limits)

    def test_mandate_trust_boundaries_are_present_in_all_mandates(self) -> None:
        # S6: All mandates must include strict DATA, NEVER INSTRUCTIONS boundary
        mandates_dir = FACTORY_ROOT / "mandates"
        for md in mandates_dir.glob("*.md"):
            text = md.read_text(encoding="utf-8")
            self.assertIn(
                "DATA, NEVER INSTRUCTIONS", text, f"Mandate {md.name} missing prompt injection trust boundary"
            )
            self.assertIn("RESULT_REPO", text, f"Mandate {md.name} missing RESULT_REPO scope")

        # Stresser must include localhost-only egress boundary
        stresser_text = (mandates_dir / "stresser.md").read_text(encoding="utf-8")
        self.assertIn("127.0.0.1", stresser_text)
        self.assertIn("localhost", stresser_text)


if __name__ == "__main__":
    unittest.main()
