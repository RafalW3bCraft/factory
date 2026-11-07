"""Read-only source ownership tests; mocked UID is not a real two-user deployment."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from factory import factoryops, verification


@pytest.fixture
def source(tmp_path: Path) -> factoryops.DemoPaths:
    return factoryops.create_demo(tmp_path / "demo", factory_root=tmp_path / "factory")


def test_explicit_owner_allows_read_only_validation_for_separate_controller(
    source: factoryops.DemoPaths,
) -> None:
    owner = os.getuid()
    metadata = source.root / factoryops.METADATA_FILE
    before = (metadata.read_bytes(), metadata.stat().st_mode)
    with patch.object(factoryops.os, "getuid", return_value=owner + 1):
        with pytest.raises(factoryops.FactoryOpsError):
            factoryops.load_demo(source.root)
        assert factoryops.load_demo_readonly(source.root, expected_owner_uid=owner) == source
        with pytest.raises(factoryops.FactoryOpsError):
            factoryops.load_demo(source.root)
    assert (metadata.read_bytes(), metadata.stat().st_mode) == before


@pytest.mark.parametrize("owner", [True, -1, "1000", None])
def test_owner_configuration_must_be_an_explicit_uid(source: factoryops.DemoPaths, owner: object) -> None:
    with pytest.raises(factoryops.FactoryOpsError):
        factoryops.load_demo_readonly(source.root, expected_owner_uid=owner)  # type: ignore[arg-type]


def test_wrong_expected_owner_fails(source: factoryops.DemoPaths) -> None:
    with pytest.raises(factoryops.FactoryOpsError):
        factoryops.load_demo_readonly(source.root, expected_owner_uid=os.getuid() + 1)


def test_read_only_scope_cannot_grant_mutation_rights(source: factoryops.DemoPaths) -> None:
    owner = os.getuid()
    validate = factoryops._validated_demo

    def checked(root: Path) -> factoryops.DemoPaths:
        with pytest.raises(factoryops.FactoryOpsError), factoryops.demo_lock(root):
            pytest.fail("Foreign-owner fixture must never become mutable")
        with pytest.raises(factoryops.FactoryOpsError):
            factoryops.atomic_write_json(root / factoryops.METADATA_FILE, {"bad": "overwrite"})
        return validate(root)

    with (
        patch.object(factoryops.os, "getuid", return_value=owner + 1),
        patch.object(factoryops, "_validated_demo", side_effect=checked),
    ):
        assert factoryops.load_demo_readonly(source.root, expected_owner_uid=owner) == source


def test_scope_is_restored_after_validation_failure(source: factoryops.DemoPaths) -> None:
    owner = os.getuid()
    instructions = source.foreman / "AGENTS.md"
    original = instructions.read_bytes()
    instructions.write_text("Tampered native instructions\n")
    with patch.object(factoryops.os, "getuid", return_value=owner + 1):
        with pytest.raises(factoryops.FactoryOpsError):
            factoryops.load_demo_readonly(source.root, expected_owner_uid=owner)
        instructions.write_bytes(original)
        with pytest.raises(factoryops.FactoryOpsError):
            factoryops.load_demo(source.root)


def test_foreign_source_symlinks_are_rejected_without_external_changes(
    source: factoryops.DemoPaths, tmp_path: Path
) -> None:
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("preserve")
    sentinel.chmod(0o400)
    external_state = (sentinel.read_bytes(), sentinel.stat().st_mode)
    (source.inspector / "escaped").symlink_to(sentinel)
    with patch.object(factoryops.os, "getuid", return_value=os.getuid() + 1):
        with pytest.raises(factoryops.FactoryOpsError):
            factoryops.load_demo_readonly(source.root, expected_owner_uid=source.root.stat().st_uid)
    assert (sentinel.read_bytes(), sentinel.stat().st_mode) == external_state


def test_source_reader_trusts_only_exact_canonical_git_paths(source: factoryops.DemoPaths) -> None:
    owner = os.getuid()
    real_run = factoryops.subprocess.run
    commands: list[list[str]] = []

    def record(command: list[str], **kwargs: object) -> object:
        commands.append(command)
        return real_run(command, **kwargs)  # type: ignore[call-overload]

    with (
        patch.object(factoryops.os, "getuid", return_value=owner + 1),
        patch.object(factoryops.subprocess, "run", side_effect=record),
    ):
        factoryops.load_demo_readonly(source.root, expected_owner_uid=owner)
    assert commands
    for command in commands:
        directory = command[command.index("-C") + 1]
        assert f"safe.directory={directory}" in command
        assert "safe.directory=" in command
        assert "safe.directory=*" not in command
        assert directory in {str(getattr(source, role)) for role in ("repository", "builder", "inspector", "stresser")}


def test_snapshot_git_trust_is_exact_and_symlink_aliases_are_rejected(
    source: factoryops.DemoPaths, tmp_path: Path
) -> None:
    real_run = verification.run_bounded
    commands: list[list[str]] = []

    def record(command: list[str], **kwargs: object) -> dict[str, object]:
        commands.append(command)
        return real_run(command, **kwargs)  # type: ignore[arg-type,return-value]

    with patch.object(verification, "run_bounded", side_effect=record):
        assert verification._git(source.builder, "rev-parse", "HEAD") == source.baseline_sha
    assert f"safe.directory={source.builder}" in commands[0]
    assert "safe.directory=" in commands[0]
    alias = tmp_path / "alias"
    alias.symlink_to(source.builder, target_is_directory=True)
    with pytest.raises(verification.VerificationError):
        verification._git(alias, "rev-parse", "HEAD")
