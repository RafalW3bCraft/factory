"""Completion instructions describe actual guarantees, never grant authority."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from factory import factoryops


def test_default_supervised_mode_is_persisted_and_labelled(tmp_path: Path) -> None:
    paths = factoryops.create_demo(tmp_path / "demo", factory_root=tmp_path / "factory")
    metadata = json.loads((paths.root / factoryops.METADATA_FILE).read_text())
    assert metadata["completion_mode"] == "supervised"
    assert factoryops.load_demo(paths.root).completion_mode == "supervised"
    for role in ("foreman", "builder", "inspector", "stresser"):
        instructions = (getattr(paths, role) / "AGENTS.md").read_text()
        assert "Completion mode: supervised" in instructions
        assert "human-reviewed demonstration" in instructions
        assert "not an authoritative release decision" in instructions


def test_enforced_mode_requires_trusted_signed_report(tmp_path: Path) -> None:
    paths = factoryops.create_demo(tmp_path / "demo", factory_root=tmp_path / "factory", completion_mode="enforced")
    assert factoryops.load_demo(paths.root).completion_mode == "enforced"
    instructions = (paths.foreman / "AGENTS.md").read_text()
    assert "Completion mode: enforced" in instructions
    assert "signed trusted controller artifact" in instructions
    assert "BLOCKED" in instructions


def test_invalid_completion_mode_is_rejected_before_creating_fixture(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    with pytest.raises(factoryops.FactoryOpsError):
        factoryops.create_demo(root, factory_root=tmp_path / "factory", completion_mode="autonomous")
    assert not root.exists()


def test_legacy_schema_two_stays_valid_without_implicit_instruction_rewrite(tmp_path: Path) -> None:
    paths = factoryops.create_demo(tmp_path / "demo", factory_root=tmp_path / "factory")
    metadata_path = paths.root / factoryops.METADATA_FILE
    metadata = json.loads(metadata_path.read_text())
    metadata.pop("completion_mode", None)
    metadata_path.write_text(json.dumps(metadata))
    for role in ("foreman", "builder", "inspector", "stresser"):
        (getattr(paths, role) / "AGENTS.md").write_text(factoryops._role_instructions(role, None))
    before = metadata_path.read_bytes()
    assert factoryops.load_demo(paths.root).completion_mode == "supervised"
    assert metadata_path.read_bytes() == before


def test_mode_and_instruction_mismatch_blocks_use(tmp_path: Path) -> None:
    paths = factoryops.create_demo(tmp_path / "demo", factory_root=tmp_path / "factory")
    metadata_path = paths.root / factoryops.METADATA_FILE
    metadata = json.loads(metadata_path.read_text())
    metadata["completion_mode"] = "enforced"
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(factoryops.FactoryOpsError):
        factoryops.load_demo(paths.root)


@pytest.mark.parametrize("mode", ["supervised", "enforced", None])
def test_preparation_preserves_explicit_and_legacy_mode(tmp_path: Path, mode: str | None) -> None:
    paths = factoryops.create_demo(
        tmp_path / "demo", factory_root=tmp_path / "factory", completion_mode=mode or "supervised"
    )
    metadata_path = paths.root / factoryops.METADATA_FILE
    if mode is None:
        metadata = json.loads(metadata_path.read_text())
        metadata.pop("completion_mode")
        metadata_path.write_text(json.dumps(metadata))
        for role in ("foreman", "builder", "inspector", "stresser"):
            (getattr(paths, role) / "AGENTS.md").write_text(factoryops._role_instructions(role, None))
    (paths.builder / "src/inventory.py").write_text("# Disposable exact-revision candidate\n")
    for command in (["add", "src/inventory.py"], ["commit", "-m", "test: disposable candidate"]):
        subprocess.run(["git", "-C", str(paths.builder), *command], check=True, capture_output=True)
    candidate = subprocess.check_output(["git", "-C", str(paths.builder), "rev-parse", "HEAD"], text=True).strip()
    factoryops.prepare_verifier_checkout(paths.root, "inspector", candidate)
    assert factoryops.load_demo(paths.root).completion_mode == (mode or "supervised")
    assert json.loads(metadata_path.read_text()).get("completion_mode") == mode


@pytest.mark.parametrize("mode", ["autonomous", None, True, {}, []])
def test_malformed_persisted_mode_is_a_controlled_error(tmp_path: Path, mode: object) -> None:
    paths = factoryops.create_demo(tmp_path / "demo", factory_root=tmp_path / "factory")
    metadata_path = paths.root / factoryops.METADATA_FILE
    metadata = json.loads(metadata_path.read_text())
    metadata["completion_mode"] = mode
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(factoryops.FactoryOpsError):
        factoryops.load_demo(paths.root)


def test_template_uses_explicit_modes_without_unconditional_enforced_gate() -> None:
    path = Path(__file__).resolve().parents[1] / "switch/factoryops.template.yaml"
    template = yaml.safe_load(path.read_text())
    mode = template["params"]["completion_mode"]
    assert mode["default"] == "supervised"
    assert mode["pattern"] == "supervised|enforced"
    instructions = " ".join(template["agents"][0]["instructions"].split())
    assert "Completion mode: {completion_mode}" in instructions
    assert "human-reviewed demonstration" in instructions
    assert "signed trusted controller artifact" in instructions
    assert "mode mismatch" in instructions.lower()


def test_native_runtime_credentials_stay_out_of_git_and_verifier_preparation(tmp_path: Path) -> None:
    from factory.factoryops import _run_git, create_demo, prepare_verifier_checkout

    paths = create_demo(tmp_path / "runtime-fixture", factory_root=tmp_path / "source")
    for role in ("builder", "inspector", "stresser"):
        workspace = getattr(paths, role)
        runtime = workspace / ".switch/agents"
        runtime.mkdir(parents=True)
        (runtime / "test-only.json").write_text('{"synthetic_test_credential":true}')
        assert _run_git(workspace, "status", "--porcelain", "--untracked-files=all") == ""
    target = paths.builder / "src/inventory.py"
    target.write_text(target.read_text().replace("self.quantity += amount", "self.quantity += max(0, amount)"))
    _run_git(paths.builder, "add", "src/inventory.py")
    _run_git(paths.builder, "commit", "--no-gpg-sign", "-m", "test: disposable native runtime preparation")
    sha = _run_git(paths.builder, "rev-parse", "HEAD")
    for role in ("inspector", "stresser"):
        assert prepare_verifier_checkout(paths.root, role, sha) == sha
        assert _run_git(getattr(paths, role), "status", "--porcelain", "--untracked-files=all") == ""
        assert (getattr(paths, role) / ".switch/agents/test-only.json").is_file()


def test_native_directory_inputs_are_only_agent_workspace_bindings() -> None:
    """Console resolves directory controls through agent workspace setup.

    A tooling path used only inside instructions must remain an independent
    absolute string; otherwise Console substitutes the Foreman workspace.
    """
    path = Path(__file__).resolve().parents[1] / "switch/factoryops.template.yaml"
    template = yaml.safe_load(path.read_text())
    workspace_bindings = {agent["directory"] for agent in template["agents"]}
    for name, param in template["params"].items():
        if param["type"] == "directory":
            assert "{" + name + "}" in workspace_bindings
    tooling = template["params"]["tooling_directory"]
    assert tooling["type"] == "string"
    assert tooling["pattern"] == "/.*"
