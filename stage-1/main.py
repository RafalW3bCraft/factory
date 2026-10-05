#!/usr/bin/env python3
"""Pocketful Stage 1: payments, requests, splits, settlements.

Single-process, stdlib-only HTTP service. All state is in memory and every
state access happens under one global re-entrant lock, which makes balance
mutations, idempotency-key claims and snapshots atomic by construction.
"""

import hashlib
import hmac
import json
import math
import os
import re
import secrets
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

MAX_AMOUNT = 1_000_000_000
MAX_NOTE_LEN = 200
MAX_KEY_LEN = 255
MAX_BODY_BYTES = 32 * 1024 * 1024
HANDLE_RE = re.compile(r"^[a-z0-9_]{1,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
STATUSES = ("pending", "paid", "declined", "cancelled")
VISIBILITIES = ("public", "private")


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def err(status, code, message):
    raise ApiError(status, code, message)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_token():
    return secrets.token_urlsafe(32)


def new_id(prefix):
    return prefix + "_" + secrets.token_hex(10)


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt),
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=32,
        maxmem=64 * 1024 * 1024,
    )
    return {"salt": salt, "hash": digest.hex()}


def verify_password(password, record):
    try:
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(record["salt"]),
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=32,
            maxmem=64 * 1024 * 1024,
        )
    except Exception:
        return False
    return hmac.compare_digest(digest.hex(), record["hash"])


# ---------------------------------------------------------------------------
# Body parsing / canonicalisation
# ---------------------------------------------------------------------------

def _reject_constant(name):
    raise ValueError("invalid JSON constant: %s" % name)


def parse_json_object(raw):
    """Parse a request body into a dict. A 0-byte or unparseable body is 400."""
    if not raw:
        err(400, "malformed_request", "request body must be a JSON object")
    try:
        value = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except Exception:
        err(400, "malformed_request", "request body is not valid JSON")
    if not isinstance(value, dict):
        err(400, "malformed_request", "request body must be a JSON object")
    return value


def _normalize(value):
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return int(value)
        return value
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    return value


def canonical_body(parsed):
    """JSON-value equality with int/float integral values unified; bools kept distinct."""
    return json.dumps(_normalize(parsed), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Field parsers
# ---------------------------------------------------------------------------

def require_field(body, name):
    if name not in body:
        err(422, "validation_failed", "field '%s' is required" % name)
    return body[name]


def parse_string_field(body, name):
    value = require_field(body, name)
    if not isinstance(value, str):
        err(400, "malformed_request", "field '%s' must be a string" % name)
    return value


def parse_amount(body):
    value = require_field(body, "amount")
    if isinstance(value, bool):
        err(422, "validation_failed", "amount must be an integer number of minor units")
    if isinstance(value, int):
        amount = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            err(422, "validation_failed", "amount must be an integer number of minor units")
        amount = int(value)
    elif value is None or isinstance(value, (list, dict)):
        err(400, "malformed_request", "amount must be a number")
    else:
        err(422, "validation_failed", "amount must be an integer number of minor units")
    if amount < 1 or amount > MAX_AMOUNT:
        err(422, "validation_failed", "amount must be between 1 and %d" % MAX_AMOUNT)
    return amount


def parse_note(body):
    if "note" not in body:
        return ""
    value = body["note"]
    if not isinstance(value, str):
        err(422, "validation_failed", "note must be a string")
    if len(value) > MAX_NOTE_LEN:
        err(422, "validation_failed", "note must be at most %d characters" % MAX_NOTE_LEN)
    return value


def parse_visibility(body):
    value = body.get("visibility", "public")
    if value not in VISIBILITIES:
        err(422, "validation_failed", "visibility must be 'public' or 'private'")
    return value


def parse_limit_offset(query):
    def plain_int(name, default, minimum, maximum):
        if name not in query:
            return default
        raw = query[name][0]
        if not re.fullmatch(r"[0-9]+", raw):
            err(422, "validation_failed", "%s must be a plain decimal integer" % name)
        value = int(raw)
        if value < minimum or (maximum is not None and value > maximum):
            err(422, "validation_failed", "%s out of range" % name)
        return value

    limit = plain_int("limit", 50, 1, 200)
    offset = plain_int("offset", 0, 0, None)
    return limit, offset


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class Store:
    """All state; guarded by `lock`. Field names mirror the exported format."""

    def __init__(self):
        self.lock = threading.RLock()
        state = self._fresh_state()
        Store._rebuild(state)
        self.state = state

    @staticmethod
    def _fresh_state():
        return {
            "currency": "EUR",
            "minor_units": 2,
            "operators": [],
            "users": [],
            "balances": {},
            "tokens": {},
            "payments": [],
            "requests": [],
            "splits": [],
            "settlements": [],
            "idempotency": [],
        }

    # ---- indexes ---------------------------------------------------------

    @staticmethod
    def _rebuild(state):
        state["users_by_id"] = {u["id"]: u for u in state["users"]}
        state["users_by_email"] = {u["email"]: u for u in state["users"]}
        state["users_by_handle"] = {u["handle"]: u for u in state["users"]}
        state["payments_by_id"] = {p["payment_id"]: p for p in state["payments"]}
        state["requests_by_id"] = {r["request_id"]: r for r in state["requests"]}

    # ---- receipts --------------------------------------------------------

    @staticmethod
    def _currency(state):
        return state["currency"]

    @staticmethod
    def payment_receipt(state, p):
        return {
            "payment_id": p["payment_id"],
            "from_user_id": p["from_user_id"],
            "from_handle": p["from_handle"],
            "to_user_id": p["to_user_id"],
            "to_handle": p["to_handle"],
            "amount": p["amount"],
            "currency": state["currency"],
            "note": p["note"],
            "visibility": p["visibility"],
            "request_id": p["request_id"],
            "settlement_id": p["settlement_id"],
            "created_at": p["created_at"],
        }

    @staticmethod
    def request_receipt(state, r):
        return {
            "request_id": r["request_id"],
            "requester_id": r["requester_id"],
            "requester_handle": r["requester_handle"],
            "payer_id": r["payer_id"],
            "payer_handle": r["payer_handle"],
            "amount": r["amount"],
            "currency": state["currency"],
            "note": r["note"],
            "status": r["status"],
            "payment_id": r["payment_id"],
            "created_at": r["created_at"],
        }

    # ---- money -----------------------------------------------------------

    @staticmethod
    def move_money(state, from_user, to_user, amount, note, visibility,
                   request_id=None, settlement_id=None, created_at=None):
        """Debit + credit as one step. Caller holds the lock and has checked funds."""
        from_bal = state["balances"][from_user["id"]]
        to_bal = state["balances"][to_user["id"]]
        state["balances"][from_user["id"]] = from_bal - amount
        state["balances"][to_user["id"]] = to_bal + amount
        payment = {
            "payment_id": new_id("p"),
            "from_user_id": from_user["id"],
            "from_handle": from_user["handle"],
            "to_user_id": to_user["id"],
            "to_handle": to_user["handle"],
            "amount": amount,
            "note": note,
            "visibility": visibility,
            "request_id": request_id,
            "settlement_id": settlement_id,
            "created_at": created_at or now_iso(),
        }
        state["payments"].append(payment)
        state["payments_by_id"][payment["payment_id"]] = payment
        return payment

    @staticmethod
    def create_request(state, requester, payer, amount, note, created_at=None):
        request = {
            "request_id": new_id("rq"),
            "requester_id": requester["id"],
            "requester_handle": requester["handle"],
            "payer_id": payer["id"],
            "payer_handle": payer["handle"],
            "amount": amount,
            "note": note,
            "status": "pending",
            "payment_id": None,
            "created_at": created_at or now_iso(),
        }
        state["requests"].append(request)
        state["requests_by_id"][request["request_id"]] = request
        return request

    # ---- idempotency -----------------------------------------------------

    @staticmethod
    def find_idem(state, user_id, method, path, key):
        for rec in state["idempotency"]:
            if rec["user_id"] == user_id and rec["method"] == method \
                    and rec["path"] == path and rec["key"] == key:
                return rec
        return None

    @staticmethod
    def claim_idem(state, user_id, method, path, key, body_canonical, response):
        state["idempotency"].append({
            "user_id": user_id,
            "method": method,
            "path": path,
            "key": key,
            "body": body_canonical,
            "status": 201,
            "response": response,
        })

    # ---- export / import -------------------------------------------------

    def export_state(self):
        with self.lock:
            snapshot = {k: json.loads(json.dumps(v, ensure_ascii=False))
                        for k, v in self.state.items()
                        if k in ("currency", "minor_units", "operators", "users",
                                 "balances", "tokens", "payments", "requests",
                                 "splits", "settlements", "idempotency")}
        return snapshot

    @staticmethod
    def validate_snapshot(snapshot):
        """Return a validated private copy of an imported state, or raise 422."""
        if not isinstance(snapshot, dict):
            err(422, "validation_failed", "state must be a JSON object")
        required = {
            "currency": str, "minor_units": int, "operators": list, "users": list,
            "balances": dict, "tokens": dict, "payments": list, "requests": list,
            "splits": list, "settlements": list, "idempotency": list,
        }
        for key, typ in required.items():
            if key not in snapshot:
                err(422, "validation_failed", "state is missing '%s'" % key)
            value = snapshot[key]
            if isinstance(value, bool) or not isinstance(value, typ):
                err(422, "validation_failed", "state field '%s' has the wrong type" % key)

        def is_int(v):
            return isinstance(v, int) and not isinstance(v, bool)

        def check_str(obj, key, where):
            if key not in obj or not isinstance(obj[key], str):
                err(422, "validation_failed", "%s has an invalid '%s'" % (where, key))

        state = Store._fresh_state()
        state["currency"] = snapshot["currency"]
        state["minor_units"] = snapshot["minor_units"]
        if state["minor_units"] not in (0, 2, 3):
            err(422, "validation_failed", "invalid minor_units in state")
        seen_ids, seen_emails, seen_handles = set(), set(), set()
        for user in snapshot["users"]:
            if not isinstance(user, dict):
                err(422, "validation_failed", "invalid user in state")
            for key in ("id", "email", "display_name", "handle"):
                check_str(user, key, "user")
            password = user.get("password")
            if not isinstance(password, dict) or not isinstance(password.get("salt"), str) \
                    or not isinstance(password.get("hash"), str):
                err(422, "validation_failed", "invalid stored password for user")
            if not HANDLE_RE.match(user["handle"]):
                err(422, "validation_failed", "invalid handle in state")
            if user["id"] in seen_ids or user["email"] in seen_emails \
                    or user["handle"] in seen_handles:
                err(422, "validation_failed", "duplicate user identity in state")
            seen_ids.add(user["id"])
            seen_emails.add(user["email"])
            seen_handles.add(user["handle"])
            state["users"].append(user)
        for user in state["users"]:
            state["balances"][user["id"]] = 0
        for uid, balance in snapshot["balances"].items():
            if uid not in seen_ids or not is_int(balance) or balance < 0:
                err(422, "validation_failed", "invalid balance in state")
            state["balances"][uid] = balance
        for token, uid in snapshot["tokens"].items():
            if not isinstance(token, str) or not token or uid not in seen_ids:
                err(422, "validation_failed", "invalid token in state")
            state["tokens"][token] = uid
        for uid in snapshot["operators"]:
            if not isinstance(uid, str) or uid not in seen_ids:
                err(422, "validation_failed", "invalid settlement operator in state")
            state["operators"].append(uid)
        payment_ids = set()
        for payment in snapshot["payments"]:
            if not isinstance(payment, dict):
                err(422, "validation_failed", "invalid payment in state")
            for key in ("payment_id", "from_user_id", "from_handle", "to_user_id",
                        "to_handle", "note", "visibility", "created_at"):
                check_str(payment, key, "payment")
            if not is_int(payment.get("amount")) or payment["amount"] < 0 \
                    or payment["amount"] > MAX_AMOUNT:
                err(422, "validation_failed", "invalid payment amount in state")
            if payment["visibility"] not in VISIBILITIES:
                err(422, "validation_failed", "invalid payment visibility in state")
            if payment["from_user_id"] not in seen_ids or payment["to_user_id"] not in seen_ids:
                err(422, "validation_failed", "payment references unknown user in state")
            if payment["payment_id"] in payment_ids:
                err(422, "validation_failed", "duplicate payment id in state")
            request_id = payment.get("request_id")
            if request_id is not None and not isinstance(request_id, str):
                err(422, "validation_failed", "invalid payment request_id in state")
            settlement_id = payment.get("settlement_id")
            if settlement_id is not None and not isinstance(settlement_id, str):
                err(422, "validation_failed", "invalid payment settlement_id in state")
            payment_ids.add(payment["payment_id"])
            state["payments"].append(payment)
        request_ids = set()
        for request in snapshot["requests"]:
            if not isinstance(request, dict):
                err(422, "validation_failed", "invalid request in state")
            for key in ("request_id", "requester_id", "requester_handle",
                        "payer_id", "payer_handle", "note", "created_at"):
                check_str(request, key, "request")
            if not is_int(request.get("amount")) or request["amount"] < 0:
                err(422, "validation_failed", "invalid request amount in state")
            if request.get("status") not in STATUSES:
                err(422, "validation_failed", "invalid request status in state")
            if request["requester_id"] not in seen_ids or request["payer_id"] not in seen_ids:
                err(422, "validation_failed", "request references unknown user in state")
            if request["request_id"] in request_ids:
                err(422, "validation_failed", "duplicate request id in state")
            payment_id = request.get("payment_id")
            if payment_id is not None and payment_id not in payment_ids:
                err(422, "validation_failed", "request references unknown payment in state")
            request_ids.add(request["request_id"])
            state["requests"].append(request)
        for payment in state["payments"]:
            if payment["request_id"] is not None and payment["request_id"] not in request_ids:
                err(422, "validation_failed", "payment references unknown request in state")
        for split in snapshot["splits"]:
            if not isinstance(split, dict):
                err(422, "validation_failed", "invalid split in state")
            for key in ("split_id", "note", "created_at"):
                check_str(split, key, "split")
            if not is_int(split.get("amount")) or split["amount"] < 1:
                err(422, "validation_failed", "invalid split amount in state")
            shares = split.get("shares")
            if not isinstance(shares, list):
                err(422, "validation_failed", "invalid split shares in state")
            total = 0
            for share in shares:
                if not isinstance(share, dict) or not isinstance(share.get("handle"), str) \
                        or not is_int(share.get("amount")):
                    err(422, "validation_failed", "invalid split share in state")
                total += share["amount"]
            if total != split["amount"]:
                err(422, "validation_failed", "split shares do not sum to amount")
            request_ids_list = split.get("request_ids")
            if not isinstance(request_ids_list, list) or \
                    any(rid not in request_ids for rid in request_ids_list):
                err(422, "validation_failed", "invalid split request list in state")
            state["splits"].append(split)
        settlement_ids = set()
        for settlement in snapshot["settlements"]:
            if not isinstance(settlement, dict):
                err(422, "validation_failed", "invalid settlement in state")
            for key in ("settlement_id", "committed_at"):
                check_str(settlement, key, "settlement")
            payment_ids_list = settlement.get("payment_ids")
            if not isinstance(payment_ids_list, list) or \
                    any(pid not in payment_ids for pid in payment_ids_list):
                err(422, "validation_failed", "invalid settlement payment list in state")
            settlement_ids.add(settlement["settlement_id"])
            state["settlements"].append(settlement)
        for payment in state["payments"]:
            if payment["settlement_id"] is not None and \
                    payment["settlement_id"] not in settlement_ids:
                err(422, "validation_failed", "payment references unknown settlement in state")
        keys_seen = set()
        for record in snapshot["idempotency"]:
            if not isinstance(record, dict):
                err(422, "validation_failed", "invalid idempotency record in state")
            for key in ("user_id", "method", "path", "key", "body", "response"):
                if key not in record:
                    err(422, "validation_failed", "idempotency record missing '%s'" % key)
            if not isinstance(record["user_id"], str) or record["user_id"] not in seen_ids:
                err(422, "validation_failed", "idempotency record for unknown user")
            if not isinstance(record["method"], str) or not isinstance(record["path"], str) \
                    or not isinstance(record["key"], str) or not isinstance(record["body"], str) \
                    or not isinstance(record["response"], dict):
                err(422, "validation_failed", "invalid idempotency record in state")
            marker = (record["user_id"], record["method"], record["path"], record["key"])
            if marker in keys_seen:
                err(422, "validation_failed", "duplicate idempotency key in state")
            keys_seen.add(marker)
            state["idempotency"].append(record)
        return state

    def import_state(self, snapshot):
        validated = self.validate_snapshot(snapshot)
        with self.lock:
            Store._rebuild(validated)
            self.state = validated

    def reset_state(self, state):
        with self.lock:
            Store._rebuild(state)
            self.state = state


STORE = Store()


# ---------------------------------------------------------------------------
# Fixture (reset) validation
# ---------------------------------------------------------------------------

def validate_fixture(fixture):
    if not isinstance(fixture, dict):
        err(400, "malformed_request", "fixture must be a JSON object")

    def is_int(v):
        return isinstance(v, int) and not isinstance(v, bool)

    if "currency" not in fixture:
        err(422, "validation_failed", "fixture is missing 'currency'")
    if not isinstance(fixture["currency"], str):
        err(400, "malformed_request", "fixture 'currency' must be a string")
    if "minor_units" not in fixture:
        err(422, "validation_failed", "fixture is missing 'minor_units'")
    minor_units = fixture["minor_units"]
    if isinstance(minor_units, bool) or not isinstance(minor_units, int):
        err(400, "malformed_request", "fixture 'minor_units' must be an integer")
    if minor_units not in (0, 2, 3):
        err(422, "validation_failed", "fixture 'minor_units' must be 0, 2 or 3")
    if "users" not in fixture:
        err(422, "validation_failed", "fixture is missing 'users'")
    users_raw = fixture["users"]
    if not isinstance(users_raw, list):
        err(400, "malformed_request", "fixture 'users' must be an array")
    if "payments" in fixture and not isinstance(fixture["payments"], list):
        err(400, "malformed_request", "fixture 'payments' must be an array")
    if "requests" in fixture and not isinstance(fixture["requests"], list):
        err(400, "malformed_request", "fixture 'requests' must be an array")
    if "settlement_operator_ids" in fixture and \
            not isinstance(fixture["settlement_operator_ids"], list):
        err(400, "malformed_request", "fixture 'settlement_operator_ids' must be an array")

    users = []
    seen_ids, seen_emails, seen_handles = set(), set(), set()
    for raw in users_raw:
        if not isinstance(raw, dict):
            err(400, "malformed_request", "fixture user must be an object")
        for key in ("id", "email", "password", "display_name", "handle", "balance"):
            if key not in raw:
                err(422, "validation_failed", "fixture user is missing '%s'" % key)
        for key in ("id", "email", "password", "display_name", "handle"):
            if not isinstance(raw[key], str):
                err(400, "malformed_request", "fixture user '%s' must be a string" % key)
        if not is_int(raw["balance"]):
            err(400, "malformed_request", "fixture user 'balance' must be an integer")
        if not HANDLE_RE.match(raw["handle"]):
            err(422, "validation_failed", "fixture handle is invalid")
        if raw["balance"] < 0:
            err(422, "validation_failed", "fixture balance must not be negative")
        if raw["id"] in seen_ids or raw["email"] in seen_emails \
                or raw["handle"] in seen_handles:
            err(422, "validation_failed", "fixture user identities must be unique")
        seen_ids.add(raw["id"])
        seen_emails.add(raw["email"])
        seen_handles.add(raw["handle"])
        users.append(raw)

    payments = []
    for raw in fixture.get("payments", []):
        if not isinstance(raw, dict):
            err(400, "malformed_request", "fixture payment must be an object")
        for key in ("id", "from_user_id", "to_user_id"):
            if key not in raw:
                err(422, "validation_failed", "fixture payment is missing '%s'" % key)
            if not isinstance(raw[key], str):
                err(400, "malformed_request", "fixture payment '%s' must be a string" % key)
        if raw["from_user_id"] not in seen_ids or raw["to_user_id"] not in seen_ids:
            err(422, "validation_failed", "fixture payment references an unknown user")
        if "amount" not in raw:
            err(422, "validation_failed", "fixture payment is missing 'amount'")
        amount = raw["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int):
            err(400, "malformed_request", "fixture payment 'amount' must be an integer")
        if amount < 0 or amount > MAX_AMOUNT:
            err(422, "validation_failed", "fixture payment amount out of range")
        note = raw.get("note", "")
        if not isinstance(note, str):
            err(400, "malformed_request", "fixture payment 'note' must be a string")
        visibility = raw.get("visibility", "public")
        if visibility not in VISIBILITIES:
            err(422, "validation_failed", "fixture payment visibility is invalid")
        request_id = raw.get("request_id")
        if request_id is not None and not isinstance(request_id, str):
            err(400, "malformed_request", "fixture payment 'request_id' must be a string")
        payments.append({
            "payment_id": raw["id"],
            "from_user_id": raw["from_user_id"],
            "from_handle": next(u["handle"] for u in users if u["id"] == raw["from_user_id"]),
            "to_user_id": raw["to_user_id"],
            "to_handle": next(u["handle"] for u in users if u["id"] == raw["to_user_id"]),
            "amount": amount,
            "note": note,
            "visibility": visibility,
            "request_id": request_id,
            "settlement_id": None,
            "created_at": now_iso(),
        })

    requests = []
    for raw in fixture.get("requests", []):
        if not isinstance(raw, dict):
            err(400, "malformed_request", "fixture request must be an object")
        for key in ("id", "requester_id", "payer_id"):
            if key not in raw:
                err(422, "validation_failed", "fixture request is missing '%s'" % key)
            if not isinstance(raw[key], str):
                err(400, "malformed_request", "fixture request '%s' must be a string" % key)
        if raw["requester_id"] not in seen_ids or raw["payer_id"] not in seen_ids:
            err(422, "validation_failed", "fixture request references an unknown user")
        if "amount" not in raw:
            err(422, "validation_failed", "fixture request is missing 'amount'")
        amount = raw["amount"]
        if isinstance(amount, bool) or not isinstance(amount, int):
            err(400, "malformed_request", "fixture request 'amount' must be an integer")
        if amount < 0 or amount > MAX_AMOUNT:
            err(422, "validation_failed", "fixture request amount out of range")
        note = raw.get("note", "")
        if not isinstance(note, str):
            err(400, "malformed_request", "fixture request 'note' must be a string")
        status = raw.get("status", "pending")
        if status not in STATUSES:
            err(422, "validation_failed", "fixture request status is invalid")
        payment_id = raw.get("payment_id")
        if payment_id is not None and payment_id not in {p["payment_id"] for p in payments}:
            err(422, "validation_failed", "fixture request references an unknown payment")
        requests.append({
            "request_id": raw["id"],
            "requester_id": raw["requester_id"],
            "requester_handle": next(u["handle"] for u in users if u["id"] == raw["requester_id"]),
            "payer_id": raw["payer_id"],
            "payer_handle": next(u["handle"] for u in users if u["id"] == raw["payer_id"]),
            "amount": amount,
            "note": note,
            "status": status,
            "payment_id": payment_id,
            "created_at": now_iso(),
        })

    operators = []
    for uid in fixture.get("settlement_operator_ids", []):
        if not isinstance(uid, str):
            err(400, "malformed_request", "settlement_operator_ids entries must be strings")
        if uid not in seen_ids:
            err(422, "validation_failed", "settlement operator references an unknown user")
        operators.append(uid)

    return {
        "currency": fixture["currency"],
        "minor_units": minor_units,
        "operators": operators,
        "users": [
            {
                "id": u["id"],
                "email": u["email"],
                "password": u["password"],
                "display_name": u["display_name"],
                "handle": u["handle"],
            }
            for u in users
        ],
        "balances": {u["id"]: u["balance"] for u in users},
        "tokens": {},
        "payments": payments,
        "requests": requests,
        "splits": [],
        "settlements": [],
        "idempotency": [],
    }


# ---------------------------------------------------------------------------
# Endpoint implementations (each runs inside STORE.lock unless noted)
# ---------------------------------------------------------------------------

def handle_signup(body):
    email = require_field(body, "email")
    password = require_field(body, "password")
    display_name = require_field(body, "display_name")
    if not isinstance(email, str) or not isinstance(password, str) \
            or not isinstance(display_name, str):
        err(400, "malformed_request", "email, password and display_name must be strings")
    if not EMAIL_RE.match(email):
        err(422, "validation_failed", "email must be of the form local@domain")
    if len(password) < 8:
        err(422, "validation_failed", "password must be at least 8 characters")
    local = email.split("@")[0]
    handle = re.sub(r"[^a-z0-9_]", "_", local.lower())[:20]
    password_record = hash_password(password)
    with STORE.lock:
        state = STORE.state
        if email in state["users_by_email"]:
            err(409, "email_taken", "that email is already registered")
        if handle in state["users_by_handle"]:
            err(409, "handle_taken", "the derived handle is already taken")
        user = {
            "id": new_id("u"),
            "email": email,
            "password": password_record,
            "display_name": display_name,
            "handle": handle,
        }
        state["users"].append(user)
        state["users_by_id"][user["id"]] = user
        state["users_by_email"][email] = user
        state["users_by_handle"][handle] = user
        state["balances"][user["id"]] = 0
        token = new_token()
        state["tokens"][token] = user["id"]
    return 201, {"user_id": user["id"], "display_name": display_name, "token": token}


def handle_login(body):
    email = require_field(body, "email")
    password = require_field(body, "password")
    if not isinstance(email, str) or not isinstance(password, str):
        err(400, "malformed_request", "email and password must be strings")
    with STORE.lock:
        user = STORE.state["users_by_email"].get(email)
    if user is None or not verify_password(password, user["password"]):
        err(401, "unauthenticated", "unknown email or wrong password")
    with STORE.lock:
        state = STORE.state
        if user["id"] not in state["users_by_id"]:
            err(401, "unauthenticated", "unknown email or wrong password")
        token = new_token()
        state["tokens"][token] = user["id"]
    return 200, {"user_id": user["id"], "display_name": user["display_name"], "token": token}


def handle_me(user):
    with STORE.lock:
        state = STORE.state
        current = current_user(state, user)
        return 200, {
            "user_id": current["id"],
            "display_name": current["display_name"],
            "handle": current["handle"],
            "balance": state["balances"][current["id"]],
            "currency": state["currency"],
            "minor_units": state["minor_units"],
        }


def current_user(state, user):
    """Re-resolve the caller against the live state (reset/import may have swapped it)."""
    current = state["users_by_id"].get(user["id"])
    if current is None:
        err(401, "unauthenticated", "unknown bearer token")
    return current


def idempotent_response(method, path, headers, body_raw, user, execute, gate=None):
    """Run an idempotent write path. `execute(caller, body)` returns (201, response).

    Key resolution, field validation, the state mutation and the key claim all
    happen inside one critical section, so concurrent identical requests see
    exactly one 201 and the effect is applied once. `gate` is an optional
    permission check that runs immediately after authentication, before any
    key or body handling.
    """
    if gate is not None:
        gate()
    key = headers.get("Idempotency-Key")
    if key is None or key == "":
        err(400, "missing_idempotency_key", "Idempotency-Key header is required")
    body = parse_json_object(body_raw)
    canonical = canonical_body(body)
    with STORE.lock:
        state = STORE.state
        record = Store.find_idem(state, user["id"], method, path, key)
        if record is not None:
            # Replay is resolved before field validation and resource checks.
            if record["body"] == canonical:
                return 200, record["response"]
            err(409, "idempotency_key_reuse",
                "this idempotency key was already used with a different request body")
        if len(key) > MAX_KEY_LEN:
            err(422, "validation_failed", "Idempotency-Key must be 1 to 255 characters")
        status, response = execute(current_user(state, user), body)
        Store.claim_idem(state, user["id"], method, path, key, canonical, response)
    return status, response


def handle_payment_create(user, headers, body_raw):
    def execute(caller, body):
        with STORE.lock:
            state = STORE.state
            amount = parse_amount(body)
            note = parse_note(body)
            visibility = parse_visibility(body)
            to_handle = parse_string_field(body, "to_handle")
            to_user = state["users_by_handle"].get(to_handle)
            if to_user is None:
                err(404, "not_found", "no user has that handle")
            if to_user["id"] == caller["id"]:
                err(422, "self_payment", "cannot pay yourself")
            if state["balances"][caller["id"]] < amount:
                err(409, "insufficient_funds", "balance is below the payment amount")
            payment = Store.move_money(state, caller, to_user, amount, note, visibility)
            return 201, Store.payment_receipt(state, payment)

    return idempotent_response("POST", "/payments", headers, body_raw, user, execute)


def handle_request_create(user, headers, body_raw):
    def execute(caller, body):
        with STORE.lock:
            state = STORE.state
            amount = parse_amount(body)
            note = parse_note(body)
            payer_handle = parse_string_field(body, "payer_handle")
            payer = state["users_by_handle"].get(payer_handle)
            if payer is None:
                err(404, "not_found", "no user has that handle")
            if payer["id"] == caller["id"]:
                err(422, "self_request", "cannot request from yourself")
            request = Store.create_request(state, caller, payer, amount, note)
            return 201, Store.request_receipt(state, request)

    return idempotent_response("POST", "/requests", headers, body_raw, user, execute)


def handle_request_pay(user, request_id, headers, body_raw):
    path = "/requests/%s/pay" % request_id

    def execute(caller, body):
        with STORE.lock:
            state = STORE.state
            visibility = parse_visibility(body)
            request = state["requests_by_id"].get(request_id)
            if request is None:
                err(404, "not_found", "no such request")
            if request["payer_id"] != caller["id"]:
                err(403, "forbidden", "only the payer may pay this request")
            if request["status"] != "pending":
                err(409, "request_not_pending", "the request is no longer pending")
            if state["balances"][caller["id"]] < request["amount"]:
                err(409, "insufficient_funds", "balance is below the requested amount")
            payee = state["users_by_id"][request["requester_id"]]
            payment = Store.move_money(state, caller, payee, request["amount"],
                                       request["note"], visibility,
                                       request_id=request["request_id"])
            request["status"] = "paid"
            request["payment_id"] = payment["payment_id"]
            return 201, Store.payment_receipt(state, payment)

    return idempotent_response("POST", path, headers, body_raw, user, execute)


def handle_request_decline(user, request_id):
    with STORE.lock:
        state = STORE.state
        caller = current_user(state, user)
        request = state["requests_by_id"].get(request_id)
        if request is None:
            err(404, "not_found", "no such request")
        if request["payer_id"] != caller["id"]:
            err(403, "forbidden", "only the payer may decline this request")
        if request["status"] == "declined":
            return 200, Store.request_receipt(state, request)
        if request["status"] != "pending":
            err(409, "request_not_pending", "the request is no longer pending")
        request["status"] = "declined"
        return 200, Store.request_receipt(state, request)


def handle_request_cancel(user, request_id):
    with STORE.lock:
        state = STORE.state
        caller = current_user(state, user)
        request = state["requests_by_id"].get(request_id)
        if request is None:
            err(404, "not_found", "no such request")
        if request["requester_id"] != caller["id"]:
            err(403, "forbidden", "only the requester may cancel this request")
        if request["status"] == "cancelled":
            return 200, Store.request_receipt(state, request)
        if request["status"] != "pending":
            err(409, "request_not_pending", "the request is no longer pending")
        request["status"] = "cancelled"
        return 200, Store.request_receipt(state, request)


def handle_requests_list(user, query):
    limit, offset = parse_limit_offset(query)
    direction = query.get("direction", [None])[0]
    if direction not in (None, "incoming", "outgoing"):
        err(422, "validation_failed", "direction must be 'incoming' or 'outgoing'")
    status = query.get("status", [None])[0]
    if status not in (None,) + STATUSES:
        err(422, "validation_failed", "unknown status value")
    with STORE.lock:
        state = STORE.state
        caller = current_user(state, user)
        matches = []
        for request in reversed(state["requests"]):
            is_requester = request["requester_id"] == caller["id"]
            is_payer = request["payer_id"] == caller["id"]
            if not (is_requester or is_payer):
                continue
            if direction == "incoming" and not is_payer:
                continue
            if direction == "outgoing" and not is_requester:
                continue
            if status is not None and request["status"] != status:
                continue
            matches.append(Store.request_receipt(state, request))
        page = matches[offset:offset + limit]
        return 200, {"requests": page, "has_more": len(matches) > offset + limit}


def handle_split_create(user, headers, body_raw):
    def execute(caller, body):
        with STORE.lock:
            state = STORE.state
            amount = parse_amount(body)
            note = parse_note(body)
            handles = require_field(body, "participant_handles")
            if not isinstance(handles, list):
                err(400, "malformed_request", "participant_handles must be an array")
            if len(handles) == 0:
                err(422, "validation_failed", "participant_handles must not be empty")
            for handle in handles:
                if not isinstance(handle, str):
                    err(400, "malformed_request", "participant_handles must contain strings")
            if len(set(handles)) != len(handles):
                err(422, "validation_failed", "participant_handles must not contain duplicates")
            participants = []
            for handle in handles:
                participant = state["users_by_handle"].get(handle)
                if participant is None:
                    err(404, "not_found", "no user has handle '%s'" % handle)
                participants.append(participant)
            count = len(participants)
            base, remainder = divmod(amount, count)
            shares = [base + 1 if i < remainder else base for i in range(count)]
            created_at = now_iso()
            split_id = new_id("sp")
            request_receipts = []
            request_ids = []
            for participant, share in zip(participants, shares):
                if participant["id"] == caller["id"]:
                    continue
                request = Store.create_request(state, caller, participant, share, note,
                                               created_at=created_at)
                request_ids.append(request["request_id"])
                request_receipts.append(Store.request_receipt(state, request))
            state["splits"].append({
                "split_id": split_id,
                "amount": amount,
                "note": note,
                "shares": [{"handle": p["handle"], "amount": s}
                           for p, s in zip(participants, shares)],
                "request_ids": request_ids,
                "created_at": created_at,
            })
            return 201, {
                "split_id": split_id,
                "amount": amount,
                "currency": state["currency"],
                "note": note,
                "shares": [{"handle": p["handle"], "amount": s}
                           for p, s in zip(participants, shares)],
                "requests": request_receipts,
                "created_at": created_at,
            }

    return idempotent_response("POST", "/splits", headers, body_raw, user, execute)


def handle_activity(user, query):
    limit, offset = parse_limit_offset(query)
    with STORE.lock:
        state = STORE.state
        caller = current_user(state, user)
        visible = []
        for payment in reversed(state["payments"]):
            if payment["visibility"] == "public" \
                    or payment["from_user_id"] == caller["id"] \
                    or payment["to_user_id"] == caller["id"]:
                visible.append(Store.payment_receipt(state, payment))
        page = visible[offset:offset + limit]
        return 200, {"payments": page, "has_more": len(visible) > offset + limit}


def handle_settlement_create(user, headers, body_raw):
    path = "/settlements"

    def require_operator():
        with STORE.lock:
            state = STORE.state
            caller = current_user(state, user)
            if caller["id"] not in state["operators"]:
                err(403, "forbidden", "only settlement operators may create settlements")

    def execute(caller, body):
        with STORE.lock:
            state = STORE.state
            if caller["id"] not in state["operators"]:
                err(403, "forbidden", "only settlement operators may create settlements")
            transfers = require_field(body, "transfers")
            if not isinstance(transfers, list):
                err(400, "malformed_request", "transfers must be an array")
            if len(transfers) < 1 or len(transfers) > 32:
                err(422, "validation_failed", "transfers must contain 1 to 32 entries")
            parsed = []
            for entry in transfers:
                if not isinstance(entry, dict):
                    err(400, "malformed_request", "each transfer must be an object")
                from_handle = parse_string_field(entry, "from_handle")
                to_handle = parse_string_field(entry, "to_handle")
                sender = state["users_by_handle"].get(from_handle)
                if sender is None:
                    err(404, "not_found", "no user has handle '%s'" % from_handle)
                receiver = state["users_by_handle"].get(to_handle)
                if receiver is None:
                    err(404, "not_found", "no user has handle '%s'" % to_handle)
                if sender["id"] == receiver["id"]:
                    err(422, "self_payment", "cannot transfer to yourself")
                amount = parse_amount(entry)
                note = parse_note(entry)
                visibility = parse_visibility(entry)
                parsed.append((sender, receiver, amount, note, visibility))
            nets = {}
            for sender, receiver, amount, _note, _visibility in parsed:
                nets[sender["id"]] = nets.get(sender["id"], 0) - amount
                nets[receiver["id"]] = nets.get(receiver["id"], 0) + amount
            for uid, net in nets.items():
                if state["balances"][uid] + net < 0:
                    err(409, "insufficient_funds", "the settlement is not affordable")
            settlement_id = new_id("st")
            committed_at = now_iso()
            receipts = []
            for sender, receiver, amount, note, visibility in parsed:
                payment = Store.move_money(state, sender, receiver, amount, note,
                                           visibility, request_id=None,
                                           settlement_id=settlement_id,
                                           created_at=committed_at)
                receipts.append(Store.payment_receipt(state, payment))
            state["settlements"].append({
                "settlement_id": settlement_id,
                "committed_at": committed_at,
                "payment_ids": [r["payment_id"] for r in receipts],
            })
            return 201, {
                "settlement_id": settlement_id,
                "committed_at": committed_at,
                "payments": receipts,
            }

    return idempotent_response("POST", path, headers, body_raw, user, execute,
                               gate=require_operator)


def handle_reset(body_raw):
    fixture = parse_json_object(body_raw)
    state = validate_fixture(fixture)

    def seed_password(user):
        user["password"] = hash_password(user["password"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(seed_password, state["users"]))
    STORE.reset_state(state)
    return 204, None


def handle_export():
    snapshot = STORE.export_state()
    return 200, {"track": "pocketful", "format_version": 1, "state": snapshot}


def handle_import(body_raw):
    body = parse_json_object(body_raw)
    if body.get("track") != "pocketful":
        err(422, "validation_failed", "export must have track 'pocketful'")
    version = body.get("format_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        err(422, "validation_failed", "export must have format_version 1")
    if "state" not in body:
        err(422, "validation_failed", "export is missing 'state'")
    STORE.import_state(body["state"])
    return 204, None


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "pocketful/1.0"
    timeout = 60

    def log_message(self, fmt, *args):
        pass

    # -- plumbing ----------------------------------------------------------

    def _send(self, status, payload):
        try:
            if status == 204:
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True

    def _send_error_body(self, status, code, message):
        self._send(status, {"error": {"code": code, "message": message}})

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return b""
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            err(400, "malformed_request", "request body too large")
        return self.rfile.read(length)

    def _authenticate(self):
        header = self.headers.get("Authorization")
        if not header:
            err(401, "unauthenticated", "a bearer token is required")
        parts = header.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
            err(401, "unauthenticated", "malformed authorization header")
        token = parts[1].strip()
        with STORE.lock:
            user_id = STORE.state["tokens"].get(token)
            if user_id is None:
                err(401, "unauthenticated", "unknown bearer token")
            user = STORE.state["users_by_id"].get(user_id)
            if user is None:
                err(401, "unauthenticated", "unknown bearer token")
            return user

    # -- routing -----------------------------------------------------------

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def _dispatch(self, method):
        try:
            split = urlsplit(self.path)
            segments = [unquote(s) for s in split.path.split("/") if s != ""]
            query = parse_qs(split.query, keep_blank_values=False)
            body_raw = self._read_body()
            status, payload = self._route(method, segments, query, body_raw)
            self._send(status, payload)
        except ApiError as exc:
            self._send_error_body(exc.status, exc.code, exc.message)
        except Exception:
            # The contract forbids 5xx; unexpected faults surface as a 4xx envelope.
            self._send_error_body(400, "malformed_request", "request could not be processed")

    def _route(self, method, segments, query, body_raw):
        is_get = method in ("GET", "HEAD")

        if segments == ["health"] and is_get:
            return 200, {"status": "ok"}

        if segments == ["_test", "reset"] and method == "POST":
            return handle_reset(body_raw)

        if segments == ["_test", "export"] and is_get:
            return handle_export()

        if segments == ["_test", "import"] and method == "POST":
            return handle_import(body_raw)

        if segments == ["auth", "signup"] and method == "POST":
            return handle_signup(parse_json_object(body_raw))

        if segments == ["auth", "login"] and method == "POST":
            return handle_login(parse_json_object(body_raw))

        user = self._authenticate()

        if segments == ["me"] and is_get:
            return handle_me(user)

        if segments == ["payments"] and method == "POST":
            return handle_payment_create(user, self.headers, body_raw)

        if segments == ["requests"] and is_get:
            return handle_requests_list(user, query)

        if segments == ["requests"] and method == "POST":
            return handle_request_create(user, self.headers, body_raw)

        if len(segments) == 3 and segments[0] == "requests" and method == "POST":
            request_id = segments[1]
            action = segments[2]
            if action == "pay":
                return handle_request_pay(user, request_id, self.headers, body_raw)
            if action == "decline":
                return handle_request_decline(user, request_id)
            if action == "cancel":
                return handle_request_cancel(user, request_id)

        if segments == ["splits"] and method == "POST":
            return handle_split_create(user, self.headers, body_raw)

        if segments == ["activity"] and is_get:
            return handle_activity(user, query)

        if segments == ["settlements"] and method == "POST":
            return handle_settlement_create(user, self.headers, body_raw)

        err(404, "not_found", "no such resource")


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128


def main():
    raw_port = os.environ.get("PORT") or "8080"
    try:
        port = int(raw_port)
    except ValueError:
        port = 8080
    server = Server(("0.0.0.0", port), Handler)

    def shutdown(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()