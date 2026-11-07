"""The offline sandbox must run application tooling rather than an empty shell."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_sandbox_default_has_no_network_or_credentials() -> None:
    service = yaml.safe_load((ROOT / "docker-compose.sandbox.yml").read_text())["services"]["factory-sandbox"]
    assert service["network_mode"] == "none"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert not service.get("cap_add")
    assert not any("PASSWORD" in str(v) or "API_KEY" in str(v) for v in service.get("environment", []))
    assert service["command"] == ["python", "-m", "factory.sandbox_smoke"]


def test_sandbox_image_installs_project_and_retains_runtime_resources() -> None:
    source = (ROOT / "Dockerfile.sandbox").read_text()
    assert "uv sync --frozen" in source
    assert "--no-editable" in source
    assert "COPY src/" in source
    assert 'ENTRYPOINT ["/bin/bash"]' not in source


def test_nonroot_sandbox_smoke_runs_real_fixture_locally() -> None:
    """A local runtime smoke is distinct from a container containment test."""
    from factory.sandbox_smoke import main

    assert main() == 0


def test_sandbox_dependency_downloads_have_bounded_retries_without_tls_bypass() -> None:
    """Slow links must not inherit uv's short read timeout or disable TLS."""
    import shlex

    source = (ROOT / "Dockerfile.sandbox").read_text()
    settings: dict[str, str] = {}
    for line in source.splitlines():
        if line.startswith("ENV "):
            for token in shlex.split(line[4:]):
                if "=" in token:
                    key, value = token.split("=", 1)
                    settings[key] = value
    assert 60 <= int(settings["UV_HTTP_TIMEOUT"]) <= 300
    assert 1 <= int(settings["UV_HTTP_RETRIES"]) <= 5
    assert "UV_INSECURE_HOST" not in source
    assert "--allow-insecure-host" not in source
