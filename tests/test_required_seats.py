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


@pytest.mark.parametrize("pending_approval", [False, True])
def test_expired_challenge_renews_once_and_invalidates_pending_approval(tmp_path: Path, pending_approval: bool) -> None:
    from factory.switch_gate import GateSession

    store = ledger(tmp_path)
    store.set_candidate("a" * 40, "b" * 64)
    for role in ("inspector", "stresser"):
        store.record_receipt(
            store._seal_receipt(
                {
                    "candidate_sha": "a" * 40,
                    "manifest": "b" * 64,
                    "role": role,
                    "exit_code": 0,
                    "backend": "container",
                    "isolated": True,
                    "command": ["test"],
                    "cleanup_confirmed": True,
                    "image": "sha256:" + "c" * 64,
                    "output_sha256": "d" * 64,
                    "duration_seconds": 0.01,
                }
            )
        )
    posted: list[str] = []
    config = {
        "server_url": "http://127.0.0.1:8080",
        "agent_id": "observer",
        "observer_participant_id": "observer-id",
        "room_id": "room",
        "required_seats": ROLES,
        "seat_addresses": {role: "factoryops-" + role for role in ROLES},
    }
    gate = GateSession(store, config, "conn", posted.append)

    def deliver(seq: int, sender: str, body: str) -> None:
        gate.handle(
            {
                "event": "message",
                "id": seq,
                "data": {
                    "type": "message",
                    "sequence": seq,
                    "room_id": "room",
                    "payload": {"sender": sender, "message_id": f"m{seq}", "body": body},
                },
            }
        )

    with patch("factory.workflow.time.time", return_value=1000):
        gate.handle(
            {
                "event": "connection_state",
                "data": {
                    "agent_id": "observer",
                    "connection_id": "conn",
                    "cursor": 0,
                    "generation": 1,
                    "rooms": ["room"],
                    "scope": "single",
                    "filter": "all",
                },
            }
        )
        nonce = store.status()["readiness"]["nonce"]
        sequence = 0
        if pending_approval:
            for role in ROLES:
                sequence += 1
                deliver(sequence, ROLES[role], f"FACTORYOPS_READY {role} {nonce}")
        for role in ("inspector", "stresser"):
            sequence += 1
            signature = store.status()["receipts"][role]["signature"]
            deliver(sequence, ROLES[role], f"VERIFIED {role} {'a' * 40} {signature}")
        if pending_approval:
            assert store.status()["request"] is not None
    with patch("factory.workflow.time.time", return_value=1121):
        store.heartbeat()
        sequence += 1
        deliver(sequence, "human", "status")
        assert store.status()["readiness"]["nonce"] != nonce
        assert store.status()["request"] is None
        assert store.status()["approval"] is None
    with patch("factory.workflow.time.time", return_value=1242):
        store.heartbeat()
        with pytest.raises(WorkflowError, match="bounded"):
            gate.progress()


def test_readiness_retry_budget_survives_reconnect_and_process_restart(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    store.set_candidate("a" * 40, "b" * 64)
    store.connection_ready("server", 0)
    store.begin_readiness()
    store.begin_readiness()
    store.connection_blocked("disconnected")
    restarted = ledger(tmp_path)
    restarted.connection_ready("server", 0)
    with pytest.raises(WorkflowError, match="bounded"):
        restarted.begin_readiness()
    restarted.set_candidate("c" * 40, "d" * 64)
    assert restarted.begin_readiness()["revision"] == 2
