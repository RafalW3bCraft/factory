"""Non-AI observer of the documented Switch scalar-cursor WebSocket protocol.

Uses a separately registered observer, never a native Codex session credential.
Official contract: docs.switchagents.ai/switch-rooms/internals/agent-connection.
Live compatibility remains pending until an actual operator-configured handshake.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import queue
import re
import stat
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

import httpx
from websockets.sync.client import connect

from factory.factoryops import atomic_write_json, load_demo_readonly
from factory.workflow import Ledger, WorkflowError

MAX_FRAME = 64 * 1024


def load_configuration(path: Path) -> dict[str, Any]:
    """Load a private local config. Never include its values in exception output."""
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise WorkflowError("Controller configuration must use a canonical absolute path.")
    info = path.stat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
        or info.st_nlink != 1
        or info.st_size > 16384
    ):
        raise WorkflowError("Controller configuration must be a private, owned regular file (0600).")
    try:
        data = json.loads(path.read_text())
        required = ("server_url", "agent_id", "observer_participant_id", "api_key", "room_id", "owner_id", "demo_root")
        if not isinstance(data, dict) or any(not isinstance(data.get(k), str) or not data[k] for k in required):
            raise ValueError
        url = urlsplit(data["server_url"])
        if (
            url.scheme not in ("http", "https")
            or url.hostname not in ("127.0.0.1", "::1", "localhost")
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or url.path not in ("", "/")
        ):
            raise ValueError
        _ = url.port
        source_uid = data.get("source_owner_uid", os.getuid())
        if type(source_uid) is not int or source_uid < 0:
            raise ValueError
        data["source_owner_uid"] = source_uid
        if not isinstance(data.get("seats"), dict) or set(data["seats"]) != {"inspector", "stresser"}:
            raise ValueError
        roles = {"foreman", "smith", "inspector", "stresser"}
        participants = data.get("required_seats")
        addresses = data.get("seat_addresses")
        if (
            not isinstance(participants, dict)
            or set(participants) != roles
            or not isinstance(addresses, dict)
            or set(addresses) != roles
            or any(not isinstance(value, str) or not value for value in participants.values())
            or len(set(participants.values()) | {data["owner_id"], data["observer_participant_id"]}) != 6
            or any(participants[role] != identity for role, identity in data["seats"].items())
            or any(
                not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}", value)
                for value in addresses.values()
            )
        ):
            raise ValueError
        if any("\n" in data[k] or "\r" in data[k] for k in required):
            raise ValueError
        data["server_url"] = data["server_url"].rstrip("/")
    except (ValueError, TypeError) as exc:
        raise WorkflowError(
            "Controller configuration is invalid; check private setup without printing credentials."
        ) from exc
    return data


def ledger_from_config(directory: Path, configuration: Path) -> Ledger:
    data = load_configuration(configuration)
    # State/configuration cannot live inside agent-writable fixture workspaces.
    for parent in (directory, *directory.parents, configuration.parent, *configuration.parent.parents):
        if (parent / ".factoryops-demo.json").exists() or (parent / ".git").exists():
            raise WorkflowError("Controller state and configuration must be outside repositories and demo roots.")
    paths = load_demo_readonly(Path(data["demo_root"]), expected_owner_uid=data["source_owner_uid"])
    return Ledger(
        directory,
        room_id=data["room_id"],
        owner_id=data["owner_id"],
        seats=data["seats"],
        candidate_repository=paths.builder,
        required_seats=data["required_seats"],
    )


class GateSession:
    """Translate authenticated wire envelopes into strictly correlated ledger events."""

    def __init__(
        self, store: Ledger, configuration: dict[str, Any], connection_id: str, post_message: Callable[[str], None]
    ) -> None:
        self.store = store
        self.config = configuration
        self.connection_id = connection_id
        self.post_message = post_message
        self.ready = False
        self.generation: int | None = None
        self.namespace = hashlib.sha256(
            (configuration["server_url"] + "\n" + configuration["agent_id"]).encode()
        ).hexdigest()

    @staticmethod
    def request_text(request: dict[str, Any]) -> str:
        return "FactoryOps approval required. Reply exactly to authorize this candidate:\n" + request["confirmation"]

    def challenge_seats(self) -> None:
        readiness = self.store.begin_readiness()
        body = "FactoryOps readiness check (120 seconds). Reply exactly with the text AFTER your @mention, omitting the mention:\n"
        body += "\n".join(
            f"@{self.config['seat_addresses'][role]} FACTORYOPS_READY {role} {readiness['nonce']}"
            for role in self.config["required_seats"]
        )
        self.post_message(body)

    def progress(self) -> None:
        status = self.store.status()
        if set(status["receipts"]) != {"inspector", "stresser"} or set(status["verdicts"]) != {"inspector", "stresser"}:
            return
        readiness = status.get("readiness")
        if not status["required_seats_live"]:
            if (
                readiness is None
                or readiness["revision"] != status["revision"]
                or time.time() >= readiness["expires_at"]
            ):
                self.challenge_seats()
            return
        if status["request"] is None:
            request = self.store.request_approval()
            self.post_message(self.request_text(request))

    def handle(self, frame: dict[str, Any]) -> None:
        event, data = frame.get("event"), frame.get("data")
        if not isinstance(data, dict):
            raise WorkflowError("Malformed Switch frame.")
        if not self.ready:
            if (
                event != "connection_state"
                or data.get("agent_id") != self.config["agent_id"]
                or data.get("connection_id") != self.connection_id
                or self.config["room_id"] not in data.get("rooms", [])
                or data.get("scope") != "single"
                or data.get("filter") != "all"
                or type(data.get("generation")) is not int
            ):
                raise WorkflowError("Observer handshake did not confirm identity, room, scope and filter.")
            cursor = data.get("cursor")
            if type(cursor) is not int:
                raise WorkflowError("Unsupported non-scalar Switch cursor.")
            self.store.connection_ready(self.namespace, cursor)
            self.generation = data["generation"]
            self.ready = True
            self.challenge_seats()
            return
        if event == "ping":
            self.store.heartbeat()
            return
        if event in {"gap", "refused", "evicted", "room_released", "subscription_changed"}:
            # Even a recoverable loss invalidates approval. Never auto-reclaim takeover.
            reason = "taken_over" if data.get("code") == "taken_over" else str(event)
            self.store.connection_blocked(reason)
            raise WorkflowError("Observer coverage lost; completion is withheld pending operator recovery.")
        if event not in {"message", "command", "room_join"}:
            self.store.connection_blocked("unsupported_frame")
            raise WorkflowError("Unsupported Switch protocol frame; operator verification required.")
        sequence = frame.get("id")
        if type(sequence) is not int or sequence != data.get("sequence") or data.get("type") != event:
            self.store.connection_blocked("invalid_sequence")
            raise WorkflowError("Switch scalar event cursor is invalid or unsupported.")
        self.progress()
        payload = data.get("payload")
        if not isinstance(payload, dict):
            raise WorkflowError("Malformed Switch payload.")
        if event == "message":
            required = ("sender", "message_id", "body")
            if (
                any(not isinstance(payload.get(k), str) or not payload[k] for k in required)
                or len(payload["body"]) > 8192
            ):
                raise WorkflowError("Malformed or oversized Switch message.")
            result = self.store.observe_message(
                self.namespace,
                {"sequence": sequence, "room_id": data.get("room_id"), **{key: payload[key] for key in required}},
            )
            status = self.store.status()
            request = status["request"]
            # Bind the request to its observed genuine platform message, not a caller ID.
            if (
                request
                and request["message_id"] is None
                and payload["sender"] == self.config["observer_participant_id"]
                and data.get("room_id") == self.config["room_id"]
                and payload["body"] == self.request_text(request)
            ):
                self.store.bind_request(request["request_id"], payload["message_id"], sequence)
            if result == "approved":
                self.store.write_report()
        else:
            self.store.advance_cursor(self.namespace, sequence)
        self.progress()


def serve(directory: Path, configuration: Path) -> None:
    """Run one owned observer until stopped or unsafe. No native-session takeover."""
    config = load_configuration(configuration)
    store = ledger_from_config(directory, configuration)
    lock = os.open(directory / "controller.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WorkflowError("Another controller owns this workflow.") from exc
        metadata = directory / "connection.json"
        if metadata.exists():
            if metadata.is_symlink() or metadata.stat().st_size > 16384:
                raise WorkflowError("Unsafe observer connection metadata.")
            connection = json.loads(metadata.read_text())
            uuid.UUID(connection["connection_id"])
            if connection["agent_id"] != config["agent_id"] or connection["server_url"] != config["server_url"]:
                raise WorkflowError("Observer server/agent identity changed.")
        else:
            connection = {
                "connection_id": str(uuid.uuid4()),
                "generation": None,
                "agent_id": config["agent_id"],
                "server_url": config["server_url"],
            }
            atomic_write_json(metadata, connection)
        base = config["server_url"]
        headers = {"Authorization": "Bearer " + config["api_key"]}
        path = "/agents/" + quote(config["agent_id"], safe="")
        # Explicit no proxies or redirects: a bearer must never leave the configured local server.
        with httpx.Client(base_url=base, headers=headers, timeout=3, trust_env=False, follow_redirects=False) as client:

            def post(body: str) -> None:
                response = client.post(path + "/message", json={"room_id": config["room_id"], "content": body})
                if response.status_code not in (200, 201, 202):
                    raise WorkflowError("Switch rejected the approval request; no completion issued.")

            # Bounded reconnection; takeover/refusal/gap always stops for operator attention.
            for attempt in range(3):
                status = store.status()
                parameters = {
                    "connection_id": connection["connection_id"],
                    "rooms": config["room_id"],
                    "scope": "single",
                    "filter": "all",
                    "start_from": str(status["cursor"]) if status["namespace"] else "head",
                }
                if connection["generation"] is not None:
                    parameters["expected_generation"] = str(connection["generation"])
                url = (
                    ("wss://" + base[8:] if base.startswith("https://") else "ws://" + base[7:])
                    + path
                    + "/connection/ws?"
                    + urlencode(parameters)
                )
                try:
                    with connect(
                        url,
                        additional_headers=headers,
                        proxy=None,
                        open_timeout=5,
                        close_timeout=2,
                        max_size=MAX_FRAME,
                        max_queue=32,
                        ping_interval=None,
                    ) as socket:
                        gate = GateSession(store, config, connection["connection_id"], post)
                        incoming: queue.Queue[dict[str, Any] | BaseException] = queue.Queue(maxsize=128)
                        stopped = threading.Event()

                        def receive() -> None:
                            try:
                                while not stopped.is_set():
                                    raw = socket.recv(timeout=5)
                                    frame = json.loads(raw)
                                    if frame.get("event") == "ping" and gate.ready:
                                        socket.send(json.dumps({"type": "pong", "cursor": store.status()["cursor"]}))
                                        store.heartbeat()
                                    else:
                                        incoming.put_nowait(frame)
                            except BaseException as exc:
                                try:
                                    incoming.put_nowait(exc)
                                except queue.Full:
                                    store.connection_blocked("overload")

                        reader = threading.Thread(target=receive, name="switch-observer", daemon=True)
                        reader.start()
                        try:
                            while True:
                                try:
                                    item = incoming.get(timeout=6)
                                except queue.Empty:
                                    # Pings are consumed by the reader; idle domain traffic is normal.
                                    store._require_stream()
                                    gate.progress()
                                    continue
                                if isinstance(item, BaseException):
                                    raise item
                                gate.handle(item)
                                if gate.ready and connection["generation"] != gate.generation:
                                    connection["generation"] = gate.generation
                                    atomic_write_json(metadata, connection)
                        finally:
                            stopped.set()
                            socket.close()
                            reader.join(timeout=3)
                except (WorkflowError, KeyboardInterrupt):
                    store.connection_blocked(
                        store.status()["connection"] if store.status()["connection"] != "healthy" else "stopped"
                    )
                    raise
                except Exception:
                    store.connection_blocked("disconnected")
                    if attempt == 2:
                        raise WorkflowError(
                            "Observer unavailable after bounded reconnects; inspect local Switch setup."
                        ) from None
                    time.sleep(1)
    finally:
        os.close(lock)


def register_observer(server_url: str, registration_key: str, name: str) -> dict[str, str]:
    """Explicit operator setup, once; never overwrites an existing agent name."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name):
        raise WorkflowError("Observer name is invalid.")
    # Reuse exactly the endpoint restrictions without writing credentials to disk.
    from factory.diagnostics import _health_target

    _health_target(server_url)
    body = {
        "name": name,
        "description": "FactoryOps non-AI completion authority",
        "connector_type": "factoryops-controller",
        "integration_profile": {
            "connection_model": "always_on",
            "message_exchange": True,
            "pre_invocation_mediation": [],
            "post_invocation_mediation": [],
            "event_reporting": [],
        },
    }
    with httpx.Client(timeout=5, trust_env=False, follow_redirects=False) as client:
        response = client.post(
            server_url.rstrip("/") + "/agents", json=body, headers={"Authorization": "Bearer " + registration_key}
        )
    if response.status_code not in (200, 201):
        raise WorkflowError("Observer registration failed; existing names are never overwritten.")
    data = response.json()
    if not isinstance(data.get("id"), str) or not isinstance(data.get("api_key"), str):
        raise WorkflowError("Observer registration returned an unsupported response.")
    return {"agent_id": data["id"], "api_key": data["api_key"]}
