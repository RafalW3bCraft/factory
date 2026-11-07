"""Protocol adapter tests use synthetic authenticated frames, never fake live claims."""

from __future__ import annotations

import json
import os
import queue
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from factory.switch_gate import GateSession, ledger_from_config, load_configuration
from factory.workflow import WorkflowError


def config(tmp_path: Path) -> Path:
    from factory.factoryops import create_demo, load_demo

    fixture = tmp_path / "fixture"
    paths = load_demo(fixture) if fixture.exists() else create_demo(fixture)
    path = tmp_path / "controller.json"
    path.write_text(
        json.dumps(
            {
                "server_url": "http://127.0.0.1:8080",
                "agent_id": "observer",
                "observer_participant_id": "observer-participant",
                "api_key": "synthetic-test-key",
                "room_id": "room",
                "owner_id": "human",
                "demo_root": str(paths.root),
                "seats": {"inspector": "inspector-id", "stresser": "stresser-id"},
                "required_seats": {role: role + "-id" for role in ("foreman", "smith", "inspector", "stresser")},
                "seat_addresses": {
                    role: "factoryops-" + role for role in ("foreman", "smith", "inspector", "stresser")
                },
            }
        )
    )
    path.chmod(0o600)
    return path


def test_private_configuration_and_endpoint_validation(tmp_path: Path) -> None:
    path = config(tmp_path)
    assert load_configuration(path)["agent_id"] == "observer"
    path.chmod(0o644)
    with pytest.raises(WorkflowError):
        load_configuration(path)
    path.chmod(0o600)
    data = json.loads(path.read_text())
    for url in ("http://user:key@127.0.0.1", "http://evil.invalid", "http://127.0.0.1/?token=x"):
        path.write_text(json.dumps({**data, "server_url": url}))
        with pytest.raises(WorkflowError):
            load_configuration(path)


def session(tmp_path: Path) -> GateSession:
    path = config(tmp_path)
    store = ledger_from_config(tmp_path / "state", path)
    return GateSession(store, load_configuration(path), "fixed-connection", lambda body: None)


def state() -> dict[str, Any]:
    return {
        "event": "connection_state",
        "data": {
            "agent_id": "observer",
            "connection_id": "fixed-connection",
            "cursor": 0,
            "generation": 1,
            "rooms": ["room"],
            "scope": "single",
            "filter": "all",
        },
    }


def test_handshake_is_required_and_actual_room_coverage_checked(tmp_path: Path) -> None:
    gate = session(tmp_path)
    with pytest.raises(WorkflowError):
        gate.handle({"event": "message", "data": {}, "id": 1})
    frame = state()
    frame["data"]["rooms"] = []  # type: ignore[index]
    with pytest.raises(WorkflowError):
        gate.handle(frame)


@pytest.mark.parametrize("control", ["gap", "evicted", "subscription_changed", "refused", "room_released"])
def test_control_failures_revoke_authorization(tmp_path: Path, control: str) -> None:
    gate = session(tmp_path)
    gate.handle(state())
    with pytest.raises(WorkflowError):
        gate.handle({"event": control, "data": {"code": "taken_over", "rooms": []}})
    assert gate.store.status()["stream_live"] is False


def test_domain_sequence_and_opaque_identity_are_preserved(tmp_path: Path) -> None:
    gate = session(tmp_path)
    gate.handle(state())
    frame = {
        "event": "message",
        "id": 2,
        "data": {
            "type": "message",
            "sequence": 2,
            "room_id": "room",
            "payload": {"sender": "opaque:do-not-parse", "message_id": "m2", "body": "hi", "addressed": True},
        },
    }
    gate.handle(frame)
    assert gate.store.status()["cursor"] == 2
    frame["id"] = 3
    with pytest.raises(WorkflowError):
        gate.handle(frame)
    assert os.stat(tmp_path / "state" / "workflow.sqlite3").st_mode & 0o077 == 0


def test_owned_service_reconnects_boundedly_without_leaking_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import factory.switch_gate as module

    path = config(tmp_path)
    calls: list[str] = []

    def unavailable(url: str, **kwargs: object) -> None:
        calls.append(url)
        assert "synthetic-test-key" not in url
        raise OSError("untrusted transport details must not escape")

    monkeypatch.setattr(module, "connect", unavailable)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    with pytest.raises(WorkflowError, match="bounded reconnects"):
        module.serve(tmp_path / "state", path)
    assert len(calls) == 3
    assert (tmp_path / "state" / "connection.json").exists()
    with pytest.raises(WorkflowError):
        module.serve(tmp_path / "state", path)


def test_full_authorization_adapter_with_simulated_transport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Actual ledger/signature, simulated HTTP/WebSocket: not live Switch evidence."""
    import factory.switch_gate as module

    path = config(tmp_path)
    store = ledger_from_config(tmp_path / "state", path)
    from factory.factoryops import load_demo

    sha = load_demo(Path(load_configuration(path)["demo_root"])).baseline_sha
    manifest = "b" * 64
    store.set_candidate(sha, manifest)
    for role in ("inspector", "stresser"):
        store.record_receipt(
            store._seal_receipt(
                {
                    "candidate_sha": sha,
                    "manifest": manifest,
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
    frames: queue.Queue = queue.Queue()
    issued: list[dict] = []

    def message(seq: int, sender: str, body: str) -> dict:
        return {
            "event": "message",
            "id": seq,
            "data": {
                "type": "message",
                "sequence": seq,
                "room_id": "room",
                "payload": {"sender": sender, "message_id": f"m{seq}", "body": body},
            },
        }

    class Socket:
        def recv(self, timeout: int) -> str:
            value = frames.get(timeout=timeout)
            if isinstance(value, BaseException):
                raise value
            return json.dumps(value)

        def send(self, value: str) -> None:
            assert json.loads(value)["type"] == "pong"

        def close(self) -> None:
            pass

    @contextmanager
    def connection(url: str, **kwargs: object):
        query = parse_qs(urlsplit(url).query)
        first = state()
        first["data"]["connection_id"] = query["connection_id"][0]
        frames.put(first)
        yield Socket()

    class Client:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["follow_redirects"] is False

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def post(self, endpoint: str, json: dict):
            from types import SimpleNamespace

            assert endpoint == "/agents/observer/message"
            body = json["content"]
            if body.startswith("FactoryOps readiness check"):
                for seq, line in enumerate(body.splitlines()[1:], 1):
                    command = line.split(" ", 1)[1]
                    role = command.split()[1]
                    frames.put(message(seq, role + "-id", command))
                for seq, role in enumerate(("inspector", "stresser"), 5):
                    signature = store.status()["receipts"][role]["signature"]
                    frames.put(message(seq, role + "-id", f"VERIFIED {role} {sha} {signature}"))
            else:
                frames.put(message(7, "observer-participant", body))
                frames.put(message(8, "human", body.split("\n", 1)[1]))
            return SimpleNamespace(status_code=200)

    original = module.Ledger.write_report

    def report(current):
        result = original(current)
        issued.append(current.read_report())
        frames.put(KeyboardInterrupt())
        return result

    monkeypatch.setattr(module, "connect", connection)
    monkeypatch.setattr(module.httpx, "Client", Client)
    monkeypatch.setattr(module.Ledger, "write_report", report)
    with pytest.raises(KeyboardInterrupt):
        module.serve(tmp_path / "state", path)
    assert issued[0]["report"]["candidate_sha"] == sha
    assert issued[0]["report"]["approval_message_id"] == "m8"


def test_idle_healthy_pings_do_not_consume_reconnect_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    import factory.switch_gate as module

    path = config(tmp_path)
    idle_polls: list[int] = []
    connects: list[str] = []

    class Incoming(queue.Queue):
        def get(self, block: bool = True, timeout: float | None = None):
            try:
                return super().get(block, 0.04)
            except queue.Empty:
                idle_polls.append(1)
                if len(idle_polls) >= 5:
                    raise KeyboardInterrupt()
                raise

    class Socket:
        first = True

        def recv(self, timeout: float) -> str:
            if self.first:
                self.first = False
                return json.dumps(handshake)
            time.sleep(0.01)
            return json.dumps({"event": "ping", "data": {}})

        def send(self, value: str) -> None:
            pass

        def close(self) -> None:
            pass

    handshake: dict = {}

    @contextmanager
    def connection(url: str, **kwargs: object):
        connects.append(url)
        handshake.update(state())
        handshake["data"]["connection_id"] = parse_qs(urlsplit(url).query)["connection_id"][0]
        yield Socket()

    class Client:
        def __init__(self, **kwargs: object):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object):
            pass

        def post(self, *args: object, **kwargs: object):
            from types import SimpleNamespace

            return SimpleNamespace(status_code=200)

    monkeypatch.setattr(module.queue, "Queue", Incoming)
    monkeypatch.setattr(module, "connect", connection)
    monkeypatch.setattr(module.httpx, "Client", Client)
    with pytest.raises(KeyboardInterrupt):
        module.serve(tmp_path / "state", path)
    assert len(idle_polls) == 5
    assert len(connects) == 1
