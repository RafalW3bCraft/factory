"""Built distributions must carry runtime mandates, dispatches, and ECC setup."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import UUID

from factory.config import asset_directory, install_ecc


def test_packaged_runtime_assets_are_present() -> None:
    assert (asset_directory("mandates") / "foreman.md").is_file()
    assert (asset_directory("dispatch") / "software-engineering.md.tmpl").is_file()
    assert (asset_directory("switch") / "factoryops.template.yaml").is_file()


def test_native_ecc_setup_is_repeatable_and_preserves_local_changes(tmp_path: Path) -> None:
    install_ecc(tmp_path)
    rules = tmp_path / ".agents/rules/common-security.md"
    original = rules.read_text()
    install_ecc(tmp_path)
    assert rules.read_text() == original
    rules.write_text("local rule")
    try:
        install_ecc(tmp_path)
    except ValueError:
        pass
    else:
        raise AssertionError("ECC setup must refuse overwriting modified files")
    assert rules.read_text() == "local rule"


def test_sbom_is_deterministic_and_uses_valid_uuid() -> None:
    script = Path(__file__).resolve().parent.parent / "scripts/generate_sbom.py"
    spec = importlib.util.spec_from_file_location("factory_sbom", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    packages = [{"name": "example", "version": "1.2.3"}]
    first = module.build_cyclonedx_sbom(packages)
    assert first == module.build_cyclonedx_sbom(packages)
    UUID(first["serialNumber"].removeprefix("urn:uuid:"))
