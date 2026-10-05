#!/usr/bin/env bash
# start-factory.sh — start the OpenCode server and one run_seat.py per seat.
#
# Usage:
#   ./start-factory.sh
#
# Required env / .env:
#   RESULT_REPO   absolute path of the result git repository
#   FEATHERLESS_API_KEY (loaded from .env if present)
#
# Per-seat model is read from mandates/<seat>.md "Model:" line.
#
# Process model:
#   - Starts "opencode serve" as a background process.
#   - Starts one run_seat.py per seat, each logging to logs/<seat>.log.
#   - Writes logs/started_at with the ISO-8601 start timestamp.
#   - Refuses to start if a seat process is already running (PID file check).
#   - On SIGTERM/EXIT, kills only our own child processes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_ROOT="$SCRIPT_DIR"
cd "$FACTORY_ROOT"

LOGS_DIR="$FACTORY_ROOT/logs"
SRC_DIR="$FACTORY_ROOT/src"
PID_DIR="$LOGS_DIR/pids"

MODEL="${MODEL:-zai-org/GLM-5.3-Flash}"
SEATS=(foreman smith inspector stresser)

# ── helpers ────────────────────────────────────────────────────────────────

die() { echo "ERROR: $*" >&2; exit 1; }

# Check if a TCP port is in use without lsof (not available on all distros)
port_in_use() {
    local port="$1"
    # Try ss first (available on Arch/Linux), fall back to Python
    if command -v ss >/dev/null 2>&1; then
        ss -tlnH 2>/dev/null | awk '{print $4}' | grep -q ":${port}$"
    else
        python3 -c "
import socket, sys
try:
    s = socket.create_connection(('127.0.0.1', ${port}), timeout=0.5)
    s.close(); sys.exit(0)
except: sys.exit(1)
" 2>/dev/null
    fi
}

check_not_running() {
    local seat="$1"
    local pidfile="$PID_DIR/${seat}.pid"
    if [[ -f "$pidfile" ]]; then
        local old_pid
        old_pid="$(cat "$pidfile")"
        if kill -0 "$old_pid" 2>/dev/null; then
            die "Seat '$seat' is already running (PID $old_pid). Run stop-factory.sh first."
        else
            rm -f "$pidfile"
        fi
    fi
}

# ── pre-flight ──────────────────────────────────────────────────────────────

[[ -f "$FACTORY_ROOT/.env" ]] && set -a && source "$FACTORY_ROOT/.env" && set +a

: "${RESULT_REPO:?RESULT_REPO must be set to the absolute path of the result git repository}"
[[ -d "$RESULT_REPO" ]] || die "RESULT_REPO does not exist: $RESULT_REPO"
[[ -d "$RESULT_REPO/.git" ]] || die "RESULT_REPO is not a git repository (no .git found): $RESULT_REPO. Run ./bootstrap-repo.sh $RESULT_REPO first."
[[ ! -f "$RESULT_REPO/.git/index.lock" ]] || die "Stale git lock detected: $RESULT_REPO/.git/index.lock. Remove it if no other git process is active."
BRANCH="$(git -C "$RESULT_REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
echo "[factory] Target repo: $RESULT_REPO (branch: $BRANCH)"

OPENCODE_BIN="$(command -v opencode 2>/dev/null)" || die "opencode not found on PATH"
command -v uv >/dev/null 2>&1 || die "uv not found on PATH"
FACTORY_PYTHON="$FACTORY_ROOT/.venv/bin/python"
[[ -x "$FACTORY_PYTHON" ]] || die "factory virtualenv python not found: $FACTORY_PYTHON. Run uv sync first."

mkdir -p "$LOGS_DIR" "$PID_DIR"

for seat in "${SEATS[@]}"; do
    check_not_running "$seat"
done

# Check opencode server is not already running (port 4096)
if port_in_use 4096; then
    die "Something is already listening on port 4096. Is opencode serve already running?"
fi

# Record factory script PID
echo "$$" > "$PID_DIR/factory.pid"

# ── cleanup on exit ─────────────────────────────────────────────────────────

OC_PID=""
SEAT_PIDS=()

cleanup() {
    echo "[factory] Shutting down…"
    if [[ ${#SEAT_PIDS[@]} -gt 0 ]]; then
        for pid in "${SEAT_PIDS[@]}"; do
            kill "$pid" 2>/dev/null || true
        done
    fi
    [[ -n "$OC_PID" ]] && kill "$OC_PID" 2>/dev/null || true
    # Remove PID files
    for seat in "${SEATS[@]}"; do
        rm -f "$PID_DIR/${seat}.pid"
    done
    rm -f "$PID_DIR/opencode.pid" "$PID_DIR/factory.pid"
}
trap cleanup EXIT INT TERM

# ── start opencode server ────────────────────────────────────────────────────

echo "[factory] Starting opencode serve on 127.0.0.1:4096 …"
# Run from FACTORY_ROOT, never from result repo (opencode reads opencode.json from cwd)
"$OPENCODE_BIN" serve --hostname=127.0.0.1 --port=4096 \
    >"$LOGS_DIR/opencode.log" 2>&1 &
OC_PID=$!
echo "$OC_PID" > "$PID_DIR/opencode.pid"

# Wait for server to be ready (up to 30s) — poll /api/health (returns {"healthy":true})
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:4096/api/health >/dev/null 2>&1; then
        echo "[factory] opencode ready (${i}s)."
        break
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
        echo "[factory] opencode did not become ready in 30s; check logs/opencode.log" >&2
        exit 1
    fi
done

# ── record start time ────────────────────────────────────────────────────────

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$LOGS_DIR/started_at"
echo "[factory] started_at: $(cat "$LOGS_DIR/started_at")"

# ── start seats ──────────────────────────────────────────────────────────────

for seat in "${SEATS[@]}"; do
    echo "[factory] Starting seat '$seat' …"
    RESULT_REPO="$RESULT_REPO" \
        "$FACTORY_PYTHON" "$SRC_DIR/run_seat.py" "$seat" "$MODEL" \
        >"$LOGS_DIR/${seat}.log" 2>&1 &
    pid=$!
    SEAT_PIDS+=("$pid")
    echo "$pid" > "$PID_DIR/${seat}.pid"
    echo "[factory] '$seat' started (PID $pid) → logs/${seat}.log"
    sleep 0.5
done

echo "[factory] All seats running. Waiting…"
wait
