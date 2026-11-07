"""Transactional authorization tests; synthetic platform events are not live evidence."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from factory.workflow import Ledger, WorkflowError

SHA = "a" * 40
TREE = "b" * 64
SEATS = {"inspector": "opaque-inspector", "stresser": "opaque-stresser"}


def ledger(tmp_path: Path) -> Ledger:
    return Ledger(tmp_path / "control", room_id="room-1", owner_id="opaque-human", seats=SEATS)


def receipt(store: Ledger, role: str, **changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "candidate_sha": store.status()["candidate_sha"] or SHA,
        "manifest": TREE,
        "role": role,
        "command": ["python", "-m", "unittest", "discover", "-s", "tests"],
        "exit_code": 0,
        "duration_seconds": 0.01,
        "output_sha256": "c" * 64,
        "backend": "container",
        "isolated": True,
        "cleanup_confirmed": True,
        "image": "sha256:" + "d" * 64,
    }
    data.update(changes)
    return store._seal_receipt(data)


def ready(store: Ledger, sha: str = SHA) -> dict[str, object]:
    store.set_candidate(sha, TREE)
    store.record_receipt(receipt(store, "inspector"))
    store.record_receipt(receipt(store, "stresser"))
    store.connection_ready("observer-1", 0)
    for sequence, role in enumerate(SEATS, 1):
        signature = store.status()["receipts"][role]["signature"]
        store.observe_message(
            "observer-1",
            {
                "sequence": sequence,
                "room_id": "room-1",
                "message_id": f"verdict-{sequence}",
                "sender": SEATS[role],
                "body": f"VERIFIED {role} {sha} {signature}",
            },
        )
    request = store.request_approval()
    store.bind_request(str(request["request_id"]), "request-message", 2)
    return request


def event(request: dict[str, object], sequence: int = 3, **changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "sequence": sequence,
        "room_id": "room-1",
        "message_id": f"reply-{sequence}",
        "sender": "opaque-human",
        "body": request["confirmation"],
    }
    data.update(changes)
    return data


def test_requires_executed_signed_independent_receipts(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    store.set_candidate(SHA, TREE)
    with pytest.raises(WorkflowError):
        store.request_approval()
    forged = receipt(store, "inspector")
    forged["exit_code"] = 1
    with pytest.raises(WorkflowError):
        store.record_receipt(forged)
    variations: tuple[dict[str, object], ...] = (
        {"exit_code": 1},
        {"isolated": False},
        {"candidate_sha": "d" * 40},
        {"command": []},
        {"cleanup_confirmed": False},
        {"image": "python:latest"},
        {"duration_seconds": -1},
        {"output_sha256": "incomplete"},
        {"command": "echo PASS"},
    )
    for changes in variations:
        with pytest.raises(WorkflowError):
            store.record_receipt(receipt(store, "inspector", **changes))
    store.record_receipt(receipt(store, "inspector"))
    with pytest.raises(WorkflowError):
        store.report()


@pytest.mark.parametrize(
    "sender,body",
    [
        ("opaque-inspector", None),
        ("human:forged", None),
        ("opaque-human", "I cannot approve this."),
        ("opaque-human", "yes"),
        ("opaque-human", "APPROVE " + "d" * 40),
        ("opaque-human", "DENY"),
    ],
)
def test_wrong_identity_ambiguous_denied_and_mismatched_replies_never_authorize(
    tmp_path: Path,
    sender: str,
    body: str | None,
) -> None:
    store = ledger(tmp_path)
    request = ready(store)
    store.observe_message("observer-1", event(request, sender=sender, body=body or request["confirmation"]))
    with pytest.raises(WorkflowError):
        store.report()


def test_approved_report_is_candidate_bound_durable_and_idempotent(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    request = ready(store)
    reply = event(request)
    assert store.observe_message("observer-1", reply) == "approved"
    assert store.observe_message("observer-1", reply) == "duplicate"
    reopened = ledger(tmp_path)
    # A process restart must re-establish a healthy authenticated stream.
    with pytest.raises(WorkflowError):
        reopened.report()
    reopened.connection_ready("observer-1", 3)
    report = reopened.report()
    assert report["candidate_sha"] == SHA
    assert report["approval_message_id"] == "reply-3"
    assert len(report["receipts"]) == 2
    reopened.set_candidate("d" * 40, "e" * 64)
    with pytest.raises(WorkflowError):
        reopened.report()
    assert reopened.status()["approval"] is None


def test_replay_wrong_room_namespace_gap_and_disconnect_fail_closed(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    request = ready(store)
    with pytest.raises(WorkflowError):
        store.observe_message("attacker-observer", event(request))
    assert store.observe_message("observer-1", event(request, room_id="other-room")) == "ignored"
    with pytest.raises(WorkflowError):
        store.report()
    store.connection_blocked("taken_over")
    with pytest.raises(WorkflowError):
        store.observe_message("observer-1", event(request, 2))
    assert store.status()["connection"] == "taken_over"


def test_expired_request_and_conflicting_duplicate_cannot_authorize(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    ready(store)
    store.expire_approval()
    with pytest.raises(WorkflowError):
        store.report()
    request = store.request_approval()
    store.bind_request(str(request["request_id"]), "request-2", 2)
    store.observe_message("observer-1", event(request))
    with pytest.raises(WorkflowError):
        store.observe_message("observer-1", event(request, body="DENY"))
    with pytest.raises(WorkflowError):
        store.report()


def test_atomic_concurrent_events_and_history_survive_restart(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    request = ready(store)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.observe_message("observer-1", event(request)), range(8)))
    assert results.count("approved") == 1
    assert results.count("duplicate") == 7
    assert json.loads(json.dumps(store.status()))["cursor"] == 3
    assert (tmp_path / "control" / "workflow.sqlite3").stat().st_mode & 0o077 == 0


def test_refuses_symlink_state_and_configuration_substitution(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir()
    (tmp_path / "control").symlink_to(target, target_is_directory=True)
    with pytest.raises(WorkflowError):
        ledger(tmp_path)
    (tmp_path / "control").unlink()
    store = ledger(tmp_path)
    assert store.status()["candidate_sha"] is None
    with pytest.raises(WorkflowError):
        Ledger(tmp_path / "control", room_id="room-other", owner_id="opaque-human", seats=SEATS)


def test_reverification_invalidates_prior_pass_before_execution(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    request = ready(store)
    store.observe_message("observer-1", event(request))
    assert store.report()
    store.begin_verification("stresser")
    with pytest.raises(WorkflowError):
        store.record_receipt(receipt(store, "stresser", exit_code=1))
    with pytest.raises(WorkflowError):
        store.report()
    assert "stresser" not in store.status()["receipts"]


def test_fresh_observer_adopts_server_baseline_without_skipping_resume(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    store.connection_ready("observer-1", 25)
    assert store.status()["cursor"] == 25
    store.connection_blocked("disconnected")
    with pytest.raises(WorkflowError):
        store.connection_ready("observer-1", 26)


def test_native_verifier_acknowledgments_are_required_and_identity_bound(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    store.set_candidate(SHA, TREE)
    for role in SEATS:
        store.record_receipt(receipt(store, role))
    store.connection_ready("observer-1", 0)
    with pytest.raises(WorkflowError):
        store.request_approval()

    signature = store.status()["receipts"]["inspector"]["signature"]
    assert (
        store.observe_message(
            "observer-1",
            {
                "sequence": 1,
                "room_id": "room-1",
                "message_id": "forged-verdict",
                "sender": SEATS["stresser"],
                "body": f"VERIFIED inspector {SHA} {signature}",
            },
        )
        == "ignored"
    )
    with pytest.raises(WorkflowError):
        store.request_approval()


def test_authoritative_artifact_tampering_and_revocation(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    request = ready(store)
    with pytest.raises(WorkflowError):
        store.read_report()

    store.observe_message("observer-1", event(request))
    artifact = store.write_report()
    assert store.read_report() == artifact
    path = store.directory / "completion.json"
    contents = path.read_text()
    path.write_text(contents.replace(SHA, "d" * 40))
    with pytest.raises(WorkflowError):
        store.read_report()
    path.write_text(contents)
    store.begin_verification("inspector")
    with pytest.raises(WorkflowError):
        store.read_report()


def test_failed_signed_result_and_native_rejection_revoke_old_success(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    request = ready(store)
    store.observe_message("observer-1", event(request))
    with pytest.raises(WorkflowError):
        store.record_receipt(receipt(store, "stresser", exit_code=1))
    with pytest.raises(WorkflowError):
        store.report()
    store = ledger(tmp_path / "another")
    request = ready(store)
    signature = store.status()["receipts"]["stresser"]["signature"]
    store.observe_message(
        "observer-1", event(request, sender=SEATS["stresser"], body=f"REJECT stresser {SHA} {signature}")
    )
    with pytest.raises(WorkflowError):
        store.request_approval()


def test_candidate_workspace_changes_revoke_previously_issued_report(tmp_path: Path) -> None:
    from factory.factoryops import create_demo

    paths = create_demo(tmp_path / "fixture")
    store = Ledger(
        tmp_path / "controller",
        room_id="room-1",
        owner_id="opaque-human",
        seats=SEATS,
        candidate_repository=paths.builder,
    )
    request = ready(store, paths.baseline_sha)
    store.observe_message("observer-1", event(request))
    assert store.write_report()
    inventory = paths.builder / "src/inventory.py"
    inventory.write_text(inventory.read_text() + "\n# candidate changed\n")
    with pytest.raises(WorkflowError):
        store.read_report()
    assert store.status()["receipts"] == {}
    assert store.status()["approval"] is None


def test_issued_report_is_revoked_when_approval_expires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import factory.workflow as workflow

    store = ledger(tmp_path)
    request = ready(store)
    store.observe_message("observer-1", event(request))
    store.write_report()
    expires = request["expires_at"]
    assert isinstance(expires, (int, float))
    monkeypatch.setattr(workflow.time, "time", lambda: expires + 1)
    with pytest.raises(WorkflowError):
        store.read_report()


def test_stale_verification_attempt_cannot_restore_or_revoke_newer_result(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    store.set_candidate(SHA, TREE)
    older = store.begin_verification("inspector")
    newer = store.begin_verification("inspector")
    with pytest.raises(WorkflowError):
        store.record_receipt(receipt(store, "inspector", **newer, exit_code=1))
    with pytest.raises(WorkflowError):
        store.record_receipt(receipt(store, "inspector", **older))
    assert "inspector" not in store.status()["receipts"]
    store.record_receipt(receipt(store, "inspector", **newer))
    with pytest.raises(WorkflowError):
        store.record_receipt(receipt(store, "inspector", **older, exit_code=1))
    assert store.status()["receipts"]["inspector"]["exit_code"] == 0
