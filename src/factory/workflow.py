"""Durable local completion authority, separate from ordinary agent conversation.

The directory and signing key belong to the trusted controller principal. Same-UID
agents with unrestricted host tools can bypass this boundary; use a separate OS
principal before claiming production authorization. No CLI imports receipts or
caller-supplied approval records.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import secrets
import sqlite3
import stat
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class WorkflowError(ValueError):
    """A trusted workflow invariant was not satisfied."""


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _private_directory(path: Path) -> None:
    if not path.is_absolute() or any(part.is_symlink() for part in (path, *path.parents)):
        raise WorkflowError("Controller state must use an absolute, non-symlink path.")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise WorkflowError("Controller state must be owned by this user with mode 0700.")


class Ledger:
    """SQLite-serialized candidate, receipts, cursor and approval transitions."""

    def __init__(
        self,
        directory: Path,
        *,
        room_id: str,
        owner_id: str,
        seats: dict[str, str],
        candidate_repository: Path | None = None,
        required_seats: dict[str, str] | None = None,
    ) -> None:
        if set(seats) != {"inspector", "stresser"}:
            raise WorkflowError("Both independent verifier participant IDs are required.")
        identities = [owner_id, *seats.values()]
        if not room_id or any(not x or not isinstance(x, str) for x in identities) or len(set(identities)) != 3:
            raise WorkflowError("Owner and verifier identities must be nonempty and distinct.")
        if required_seats is not None and (
            set(required_seats) != {"foreman", "smith", "inspector", "stresser"}
            or any(not isinstance(value, str) or not value for value in required_seats.values())
            or len(set(required_seats.values()) | {owner_id}) != 5
            or any(required_seats[role] != identity for role, identity in seats.items())
        ):
            raise WorkflowError("Four distinct native seat participant IDs must match the verifier identities.")
        _private_directory(directory)
        self.directory = directory
        self.path = directory / "workflow.sqlite3"
        self.key_path = directory / "receipt.key"
        self.configuration: dict[str, Any] = {
            "room_id": room_id,
            "owner_id": owner_id,
            "seats": seats,
            "candidate_repository": str(candidate_repository) if candidate_repository else None,
            "receipt_policy": 2,
            "required_seats": required_seats,
        }
        self._connected = False
        self._last_heartbeat = 0.0
        for path in (self.path, self.key_path):
            if path.is_symlink():
                raise WorkflowError("Controller state files cannot be symlinks.")
        try:
            descriptor = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as output:
                output.write(secrets.token_bytes(32))
                output.flush()
                os.fsync(output.fileno())
        key_info = self.key_path.stat()
        if key_info.st_uid != os.getuid() or stat.S_IMODE(key_info.st_mode) & 0o077:
            raise WorkflowError("Receipt signing key must be private to the controller.")
        self._key = self.key_path.read_bytes()
        if len(self._key) != 32:
            raise WorkflowError("Invalid controller signing key.")
        if not self.path.exists():
            try:
                descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
        info = self.path.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise WorkflowError("Workflow database must be private to the controller.")
        with self._transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS events (namespace TEXT, seq INTEGER, digest TEXT, PRIMARY KEY(namespace,seq))"
            )
            row = connection.execute("SELECT body FROM state WHERE id=1").fetchone()
            if row is None:
                state: dict[str, Any] = {
                    "configuration": self.configuration,
                    "workflow_id": secrets.token_hex(16),
                    "candidate_sha": None,
                    "manifest": None,
                    "revision": 0,
                    "receipts": {},
                    "approval": None,
                    "request": None,
                    "cursor": 0,
                    "namespace": None,
                    "connection": "disconnected",
                    "heartbeat_at": 0,
                    "attempts": {},
                    "verdicts": {},
                    "history": [],
                    "readiness": None,
                }
                self._save(connection, state)
            elif json.loads(row[0])["configuration"] != self.configuration:
                raise WorkflowError("Controller identity configuration differs from the durable ledger.")

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        try:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _read(connection: sqlite3.Connection) -> dict[str, Any]:
        return json.loads(connection.execute("SELECT body FROM state WHERE id=1").fetchone()[0])

    @staticmethod
    def _save(connection: sqlite3.Connection, state: dict[str, Any]) -> None:
        connection.execute("INSERT OR REPLACE INTO state(id,body) VALUES(1,?)", (_canonical(state),))

    def status(self) -> dict[str, Any]:
        with self._transaction() as connection:
            state = self._read(connection)
        state.pop("configuration")
        state["stream_live"] = state["connection"] == "healthy" and 0 <= time.time() - state.get("heartbeat_at", 0) < 6
        state["required_seats_live"] = self._seats_live(state)
        return state

    def _seats_live(self, state: dict[str, Any]) -> bool:
        readiness = state.get("readiness")
        expected = self.configuration.get("required_seats")
        return bool(
            expected
            and readiness
            and readiness["revision"] == state["revision"]
            and time.time() < readiness["expires_at"]
            and set(readiness["responses"]) == set(expected)
            and state["connection"] == "healthy"
            and 0 <= time.time() - state.get("heartbeat_at", 0) < 6
        )

    def begin_readiness(self) -> dict[str, Any]:
        """Issue one bounded challenge through the authenticated observer, not a JSON import."""
        self._require_stream()
        if not self.configuration.get("required_seats"):
            raise WorkflowError("Configure all four native seats before checking readiness.")
        with self._transaction() as connection:
            state = self._read(connection)
            readiness = {
                "nonce": secrets.token_hex(16),
                "revision": state["revision"],
                "expires_at": time.time() + 120,
                "cursor": state["cursor"],
                "responses": {},
            }
            state.update(readiness=readiness, request=None, approval=None)
            self._save(connection, state)
            return readiness

    def _require_seats(self, state: dict[str, Any]) -> None:
        if self.configuration.get("required_seats") is not None and not self._seats_live(state):
            raise WorkflowError("Fresh authenticated responses from all four native seats are required.")

    def _check_candidate_source(self) -> None:
        """Revocation follows actual Builder changes, not only an explicit set_candidate call."""
        repository = self.configuration["candidate_repository"]
        if repository is None:
            return  # Pure state-machine tests and execution-only local harnesses.
        from factory.verification import _git

        with self._transaction() as connection:
            state = self._read(connection)
            expected = state["candidate_sha"]
        if expected is None:
            return
        try:
            changed = _git(Path(repository), "rev-parse", "HEAD") != expected or bool(
                _git(Path(repository), "status", "--porcelain", "--untracked-files=all")
            )
        except (OSError, WorkflowError):
            changed = True
        if changed:
            with self._transaction() as connection:
                state = self._read(connection)
                state["history"].append(
                    {
                        "reason": "candidate_source_changed",
                        "candidate_sha": state["candidate_sha"],
                        "receipts": state["receipts"],
                        "verdicts": state["verdicts"],
                        "approval": state["approval"],
                    }
                )
                state.update(receipts={}, verdicts={}, approval=None, request=None)
                self._save(connection, state)
            raise WorkflowError("Builder revision or contents changed; fresh verification is required.")

    def set_candidate(self, candidate_sha: str, manifest: str, *, expected_revision: int | None = None) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", candidate_sha) or not re.fullmatch(r"[0-9a-f]{64}", manifest):
            raise WorkflowError("Candidate requires a full commit SHA and SHA-256 snapshot manifest.")
        with self._transaction() as connection:
            state = self._read(connection)
            if (state["candidate_sha"], state["manifest"]) == (candidate_sha, manifest):
                return
            if expected_revision is not None and state["revision"] != expected_revision:
                raise WorkflowError("Candidate changed during preparation; stale execution was discarded.")
            state["history"].append(
                {
                    "revision": state["revision"],
                    "candidate_sha": state["candidate_sha"],
                    "receipts": state["receipts"],
                    "request": state["request"],
                    "approval": state["approval"],
                }
            )
            state.update(
                candidate_sha=candidate_sha,
                manifest=manifest,
                revision=state["revision"] + 1,
                readiness=None,
                receipts={},
                attempts={},
                verdicts={},
                request=None,
                approval=None,
            )
            self._save(connection, state)

    def _seal_receipt(self, data: dict[str, Any]) -> dict[str, Any]:
        """Trusted runner only; not an import API or proof against same-UID code."""
        state = self.status()
        body = {
            "workflow_id": state["workflow_id"],
            "revision": state["revision"],
            "attempt": state.get("attempts", {}).get(data.get("role"), 0),
            **data,
        }
        signature = hmac.new(self._key, _canonical(body).encode(), hashlib.sha256).hexdigest()
        return {**body, "signature": signature}

    def record_receipt(self, receipt: dict[str, Any]) -> None:
        body = {key: value for key, value in receipt.items() if key != "signature"}
        signature = hmac.new(self._key, _canonical(body).encode(), hashlib.sha256).hexdigest()
        if not isinstance(receipt.get("signature"), str) or not hmac.compare_digest(receipt["signature"], signature):
            raise WorkflowError("Receipt was not issued by this trusted runner.")
        invalid = False
        with self._transaction() as connection:
            state = self._read(connection)
            role = receipt.get("role")
            current_binding = (
                role in self.configuration["seats"]
                and receipt.get("candidate_sha") == state["candidate_sha"]
                and receipt.get("manifest") == state["manifest"]
                and receipt.get("workflow_id") == state["workflow_id"]
                and receipt.get("revision") == state["revision"]
                and type(receipt.get("attempt")) is int
                and receipt["attempt"] == state.get("attempts", {}).get(role, 0)
            )
            successful = (
                type(receipt.get("exit_code")) is int
                and receipt["exit_code"] == 0
                and receipt.get("backend") == "container"
                and receipt.get("isolated") is True
                and isinstance(receipt.get("command"), list)
                and bool(receipt["command"])
                and all(isinstance(arg, str) and arg for arg in receipt["command"])
                and receipt.get("cleanup_confirmed") is True
                and isinstance(receipt.get("image"), str)
                and re.fullmatch(r"sha256:[0-9a-f]{64}", receipt["image"]) is not None
                and isinstance(receipt.get("output_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", receipt["output_sha256"]) is not None
                and type(receipt.get("duration_seconds")) in (int, float)
                and math.isfinite(receipt["duration_seconds"])
                and receipt["duration_seconds"] >= 0
            )
            if not current_binding:
                invalid = True  # A stale attempt cannot restore OR revoke newer evidence.
            else:
                if successful:
                    state["receipts"][role] = receipt
                else:
                    invalid = True
                    state["receipts"].pop(role, None)
                state["verdicts"].pop(role, None)
                state.update(approval=None, request=None)
                self._save(connection, state)

        if invalid:
            raise WorkflowError("Successful isolated execution for this exact candidate is required.")

    def begin_verification(self, role: str) -> dict[str, Any]:
        """Invalidate previous success BEFORE execution, including a crashed attempt."""
        if role not in self.configuration["seats"]:
            raise WorkflowError("Unknown verifier role.")
        with self._transaction() as connection:
            state = self._read(connection)
            if not state["candidate_sha"]:
                raise WorkflowError("Select a candidate before executing verification.")
            state["receipts"].pop(role, None)
            state["verdicts"].pop(role, None)
            attempts = state.setdefault("attempts", {})
            attempts[role] = attempts.get(role, 0) + 1
            state.update(approval=None, request=None)
            self._save(connection, state)
            return {
                **{key: state[key] for key in ("workflow_id", "revision", "candidate_sha", "manifest")},
                "attempt": attempts[role],
            }

    def connection_ready(self, namespace: str, cursor: int) -> None:
        if not namespace or type(cursor) is not int or cursor < 0:
            raise WorkflowError("Invalid authenticated observer cursor.")
        with self._transaction() as connection:
            state = self._read(connection)
            if state["namespace"] is None and state["request"] is None and state["approval"] is None:
                state["cursor"] = cursor
            if state["namespace"] not in (None, namespace) or cursor != state["cursor"]:
                raise WorkflowError("Observer identity or resume cursor changed; reconciliation required.")
            if state["connection"] in ("taken_over", "gap", "conflicting_event"):
                raise WorkflowError("Blocked stream requires operator reconciliation in a new workflow.")
            state.update(namespace=namespace, connection="healthy", heartbeat_at=time.time())
            self._save(connection, state)
        self._connected = True
        self._last_heartbeat = time.monotonic()
        with self._transaction() as connection:
            state = self._read(connection)
            state["heartbeat_at"] = time.time()
            self._save(connection, state)

    def heartbeat(self) -> None:
        if not self._connected:
            raise WorkflowError("Authenticated stream is not connected.")
        self._last_heartbeat = time.monotonic()
        with self._transaction() as connection:
            state = self._read(connection)
            if state["connection"] != "healthy":
                raise WorkflowError("Observer connection has been revoked.")
            state["heartbeat_at"] = time.time()
            self._save(connection, state)

    def connection_blocked(self, reason: str) -> None:
        self._connected = False
        with self._transaction() as connection:
            state = self._read(connection)
            state.update(connection=reason, approval=None, readiness=None)
            self._save(connection, state)

    def _require_stream(self) -> None:
        if not self._connected or time.monotonic() - self._last_heartbeat >= 6:
            raise WorkflowError("A healthy authenticated observer connection is required.")

    def request_approval(self) -> dict[str, Any]:
        self._check_candidate_source()
        self._require_stream()
        with self._transaction() as connection:
            state = self._read(connection)
            self._require_seats(state)
            if set(state["receipts"]) != {"inspector", "stresser"} or set(state["verdicts"]) != {
                "inspector",
                "stresser",
            }:
                raise WorkflowError(
                    "Both execution receipts and authenticated verifier acknowledgments must pass first."
                )
            request_id = secrets.token_hex(16)
            request = {
                "request_id": request_id,
                "candidate_sha": state["candidate_sha"],
                "confirmation": f"APPROVE {state['candidate_sha']} {request_id}",
                "created_at": time.time(),
                "expires_at": time.time() + 600,
                "message_id": None,
                "cursor": None,
            }
            state.update(request=request, approval=None)
            self._save(connection, state)
            return request

    def bind_request(self, request_id: str, message_id: str, cursor: int) -> None:
        self._require_stream()
        with self._transaction() as connection:
            state = self._read(connection)
            request = state["request"]
            if (
                not request
                or request["request_id"] != request_id
                or not message_id
                or cursor != state["cursor"]
                or request["message_id"] is not None
            ):
                raise WorkflowError("Approval request must bind its actual platform message and cursor.")
            request.update(message_id=message_id, cursor=cursor)
            self._save(connection, state)

    def expire_approval(self) -> None:
        with self._transaction() as connection:
            state = self._read(connection)
            if state["request"]:
                state["request"]["expires_at"] = 0
            state["approval"] = None
            self._save(connection, state)

    def observe_message(self, namespace: str, event: dict[str, Any]) -> str:
        """Only called by the authenticated protocol adapter, never by a CLI JSON import."""
        self._require_stream()
        self._check_candidate_source()
        required = ("room_id", "message_id", "sender", "body")
        sequence = event.get("sequence")
        if type(sequence) is not int or sequence <= 0 or any(not isinstance(event.get(k), str) for k in required):
            raise WorkflowError("Invalid platform message envelope.")
        conflict = False
        with self._transaction() as connection:
            state = self._read(connection)
            if namespace != state["namespace"]:
                raise WorkflowError("Unexpected authenticated observer namespace.")
            previous = connection.execute(
                "SELECT digest FROM events WHERE namespace=? AND seq=?", (namespace, sequence)
            ).fetchone()
            digest = _digest(event)
            if previous:
                if previous[0] == digest:
                    return "duplicate"
                state.update(connection="conflicting_event", approval=None)
                self._save(connection, state)
                conflict = True
                result = "blocked"
            else:
                if sequence <= state["cursor"]:
                    raise WorkflowError("Stale event cursor.")
                connection.execute("INSERT INTO events VALUES(?,?,?)", (namespace, sequence, digest))
                state["cursor"] = sequence
                request = state["request"]
                result = "ignored"
                if event["room_id"] == self.configuration["room_id"]:
                    readiness = state.get("readiness")
                    if (
                        readiness
                        and readiness["revision"] == state["revision"]
                        and time.time() < readiness["expires_at"]
                        and sequence > readiness["cursor"]
                    ):
                        for role, identity in (self.configuration.get("required_seats") or {}).items():
                            if (
                                event["sender"] == identity
                                and event["body"] == f"FACTORYOPS_READY {role} {readiness['nonce']}"
                            ):
                                readiness["responses"][role] = {"message_id": event["message_id"], "sequence": sequence}
                                result = "ready"
                    for role, identity in self.configuration["seats"].items():
                        receipt = state["receipts"].get(role)
                        if (
                            receipt
                            and event["sender"] == identity
                            and event["body"] == f"VERIFIED {role} {state['candidate_sha']} {receipt['signature']}"
                        ):
                            state["verdicts"][role] = {"message_id": event["message_id"], "sequence": sequence}
                            result = "verified"
                        elif (
                            receipt
                            and event["sender"] == identity
                            and event["body"] == f"REJECT {role} {state['candidate_sha']} {receipt['signature']}"
                        ):
                            state["receipts"].pop(role, None)
                            state["verdicts"].pop(role, None)
                            state.update(request=None, approval=None)
                            request = None
                            result = "rejected"
                if (
                    event["room_id"] == self.configuration["room_id"]
                    and event["sender"] == self.configuration["owner_id"]
                    and request
                    and request["message_id"]
                    and sequence > request["cursor"]
                    and time.time() < request["expires_at"]
                ):
                    if event["body"] == request["confirmation"]:
                        self._require_seats(state)
                        state["approval"] = {
                            "message_id": event["message_id"],
                            "sender": event["sender"],
                            "sequence": sequence,
                            "request_id": request["request_id"],
                            "candidate_sha": state["candidate_sha"],
                        }
                        result = "approved"
                    elif event["body"].strip().upper().startswith("DENY"):
                        request["expires_at"] = 0
                        state["approval"] = None
                        result = "denied"
                self._save(connection, state)
        if conflict:
            self._connected = False
            raise WorkflowError("Conflicting duplicate event; completion blocked.")
        self._last_heartbeat = time.monotonic()
        return result

    def advance_cursor(self, namespace: str, sequence: int) -> None:
        """Persist non-message domain events so resume never assumes contiguous messages."""
        self._require_stream()
        with self._transaction() as connection:
            state = self._read(connection)
            if namespace != state["namespace"] or type(sequence) is not int or sequence < state["cursor"]:
                raise WorkflowError("Invalid domain event cursor.")
            state["cursor"] = sequence
            self._save(connection, state)

    def report(self) -> dict[str, Any]:
        self._check_candidate_source()
        self._require_stream()
        state = self.status()
        self._require_seats(state)
        request, approval = state["request"], state["approval"]
        if (
            state["connection"] != "healthy"
            or not request
            or not approval
            or time.time() >= request["expires_at"]
            or approval["request_id"] != request["request_id"]
            or approval["candidate_sha"] != state["candidate_sha"]
            or set(state["receipts"]) != {"inspector", "stresser"}
            or set(state["verdicts"]) != {"inspector", "stresser"}
        ):
            raise WorkflowError("Completion is withheld: evidence and authenticated approval are incomplete.")
        return {
            "authority": "factoryops-controller",
            "workflow_id": state["workflow_id"],
            "candidate_sha": state["candidate_sha"],
            "manifest": state["manifest"],
            "approval_message_id": approval["message_id"],
            "request_message_id": request["message_id"],
            "receipts": state["receipts"],
            "verdicts": state["verdicts"],
            "revision": state["revision"],
            "cursor": state["cursor"],
        }

    def write_report(self) -> dict[str, Any]:
        """Create the authoritative artifact only inside the authenticated live controller."""
        from factory.factoryops import atomic_write_json

        body = self.report()
        signature = hmac.new(self._key, _canonical(body).encode(), hashlib.sha256).hexdigest()
        artifact = {"report": body, "signature": signature}
        atomic_write_json(self.directory / "completion.json", artifact)
        return artifact

    def read_report(self) -> dict[str, Any]:
        """Read an issued decision; candidate changes or evidence invalidation revoke it."""
        self._check_candidate_source()
        path = self.directory / "completion.json"
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024 * 1024:
            raise WorkflowError("No authoritative completion artifact has been issued.")
        try:
            artifact = json.loads(path.read_text())
            body = artifact["report"]
            signature = hmac.new(self._key, _canonical(body).encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(artifact["signature"], signature):
                raise WorkflowError("Completion artifact signature is invalid.")
            state = self.status()
            self._require_seats(state)
            if (
                body["workflow_id"] != state["workflow_id"]
                or body["revision"] != state["revision"]
                or body["candidate_sha"] != state["candidate_sha"]
                or not state["approval"]
                or not state["request"]
                or time.time() >= state["request"]["expires_at"]
                or body["approval_message_id"] != state["approval"]["message_id"]
                or body["receipts"] != state["receipts"]
                or body["verdicts"] != state["verdicts"]
            ):
                raise WorkflowError("Completion artifact has been revoked by a workflow change.")
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise WorkflowError("Malformed completion artifact.") from exc
        return artifact
