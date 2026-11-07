"""Authenticated challenge readiness tests; synthetic events are not live evidence."""

from pathlib import Path
from unittest.mock import patch

import pytest

from factory.workflow import Ledger, WorkflowError

ROLES = {role: role + "-id" for role in ("foreman", "smith", "inspector", "stresser")}


def ledger(tmp_path: Path) -> Ledger:
    return Ledger(
        tmp_path / "state",
        room_id="room",
        owner_id="human",
        seats={r: ROLES[r] for r in ("inspector", "stresser")},
        required_seats=ROLES,
    )


def event(seq: int, role: str, nonce: str, **changes: str) -> dict:
    return {
        "sequence": seq,
        "message_id": f"m{seq}",
        "room_id": "room",
        "sender": ROLES[role],
        "body": f"FACTORYOPS_READY {role} {nonce}",
        **changes,
    }


def test_all_four_authenticated_challenges_and_fresh_stream_required(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    store.connection_ready("server", 0)
    readiness = store.begin_readiness()
    assert store.status()["required_seats_live"] is False
    for seq, role in enumerate(ROLES, 1):
        store.observe_message("server", event(seq, role, readiness["nonce"]))
    assert store.status()["required_seats_live"] is True
    store.connection_blocked("disconnected")
    assert store.status()["required_seats_live"] is False


def test_wrong_sender_room_stale_nonce_or_candidate_cannot_supply_health(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    store.connection_ready("server", 0)
    readiness = store.begin_readiness()
    store.observe_message("server", event(1, "foreman", readiness["nonce"], sender="human"))
    store.observe_message("server", event(2, "smith", readiness["nonce"], room_id="wrong"))
    assert not store.status()["readiness"]["responses"]
    store.set_candidate("a" * 40, "b" * 64)
    for seq, role in enumerate(ROLES, 3):
        store.observe_message("server", event(seq, role, readiness["nonce"]))
    assert store.status()["required_seats_live"] is False


def test_expired_readiness_and_restart_cannot_restore_native_health(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    with patch("factory.workflow.time.time", return_value=1000):
        store.connection_ready("server", 0)
        readiness = store.begin_readiness()
        for seq, role in enumerate(ROLES, 1):
            store.observe_message("server", event(seq, role, readiness["nonce"]))
        assert store.status()["required_seats_live"] is True
    with patch("factory.workflow.time.time", return_value=1121):
        assert store.status()["required_seats_live"] is False
    restarted = ledger(tmp_path)
    with pytest.raises(WorkflowError):
        restarted.begin_readiness()


def test_heartbeat_refreshes_durable_status_for_other_processes(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    with patch("factory.workflow.time.time", return_value=1000):
        store.connection_ready("server", 0)
    with patch("factory.workflow.time.time", return_value=1005):
        store.heartbeat()
    with patch("factory.workflow.time.time", return_value=1008):
        assert store.status()["stream_live"] is True


def test_partial_required_role_configuration_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(WorkflowError):
        Ledger(
            tmp_path / "bad",
            room_id="room",
            owner_id="human",
            seats={"inspector": "i", "stresser": "s"},
            required_seats={"smith": "smith-id"},
        )
