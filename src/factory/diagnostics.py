"""Bounded, sanitized operator diagnostics; never emit tool or auth output."""

from __future__ import annotations

import http.client
import os
import re
import shutil
import subprocess
import sys
from typing import Any
from urllib.parse import urlsplit

TOOLS = ("git", "uv", "codex", "switch-console", "docker")
VERSION_RE = re.compile(r"\b\d{1,4}\.\d{1,4}(?:\.\d{1,4})?(?:-(?:alpha|beta|rc)\.?\d{0,4})?\b")


def _environment() -> dict[str, str]:
    """Pass tool discovery and local sign-in locations, never API-key variables."""
    return {name: os.environ[name] for name in ("PATH", "HOME", "CODEX_HOME", "XDG_CONFIG_HOME") if name in os.environ}


def _run(command: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        # Output is captured only for a version/boolean projection and discarded.
        return subprocess.run(
            command, capture_output=True, text=True, timeout=5, env=_environment(), stdin=subprocess.DEVNULL
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _health_target(url: str) -> tuple[str, int, bool]:
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in ("http", "https", "ws", "wss")
            or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError
        secure = parsed.scheme in ("https", "wss")
        return (
            "127.0.0.1" if parsed.hostname == "localhost" else str(parsed.hostname),
            parsed.port or (443 if secure else 80),
            secure,
        )
    except ValueError as exc:
        raise ValueError("Switch health URL must be a credential-free literal loopback base URL.") from exc


def _health(target: tuple[str, int, bool]) -> dict[str, bool]:
    host, port, secure = target
    connection = (http.client.HTTPSConnection if secure else http.client.HTTPConnection)(host, port, timeout=3)
    try:
        # http.client uses no proxy environment and does not follow redirects.
        connection.request("GET", "/health", headers={"Accept": "application/json"})
        response = connection.getresponse()
        response.read(8192)
        return {"checked": True, "reachable": True, "healthy": response.status == 200}
    except (OSError, http.client.HTTPException):
        return {"checked": True, "reachable": False, "healthy": False}
    finally:
        connection.close()


def doctor(switch_url: str | None = None) -> dict[str, Any]:
    """Return allowlisted versions, local login boolean and optional HTTP health.

    Login status is a local CLI signal, not proof of AI inference or usable
    Switch sessions. HTTP 200 is transport evidence, not authenticated readiness.
    """
    target = _health_target(switch_url) if switch_url is not None else None
    tools: dict[str, dict[str, str | bool | None]] = {}
    authenticated = False
    for name in TOOLS:
        executable = shutil.which(name)
        version = None
        if executable:
            # Electron launchers may open a second GUI rather than implement
            # --version. Query Linux package metadata without starting Console.
            package_query = shutil.which("dpkg-query") if name == "switch-console" else None
            result = (
                _run([package_query, "--show", "--showformat=${Version}", "switch-console"])
                if name == "switch-console" and package_query
                else (_run([executable, "--version"]) if name != "switch-console" else None)
            )
            if result is not None and result.returncode == 0:
                match = VERSION_RE.search(result.stdout[:4096])
                version = match.group(0) if match else None
            if name == "codex":
                login = _run([executable, "login", "status"])
                authenticated = login is not None and login.returncode == 0
        tools[name] = {"available": executable is not None, "version": version}
    return {
        "python": ".".join(str(part) for part in sys.version_info[:3]),
        "tools": tools,
        "codex_authenticated": authenticated,
        "switch_health": _health(target) if target else {"checked": False, "reachable": False, "healthy": False},
        "native_readiness": "unverified",
    }


def setup_ready(result: dict[str, Any]) -> bool:
    """Strict local prerequisites; Docker is optional for the native demo."""
    tools = result.get("tools", {})
    health = result.get("switch_health", {})
    return (
        all(tools.get(name, {}).get("available") is True for name in ("git", "uv", "codex", "switch-console"))
        and result.get("codex_authenticated") is True
        and isinstance(health, dict)
        and health.get("checked") is True
        and health.get("healthy") is True
    )
