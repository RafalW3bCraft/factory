#!/usr/bin/env bash
# start-factory.sh — start the OpenCode server and one run_seat.py per seat.
#
# Usage:   RESULT_REPO=/abs/path ./start-factory.sh
#
# Required env / .env:
#   RESULT_REPO          absolute path of the result git repository
#   FEATHERLESS_API_KEY  (loaded from .env if present)
# Optional:
#   MAX_RESTARTS         per-seat auto-restart budget (default 3)
#   TURN_TIMEOUT_S       per-turn timeout passed to the adapter (default 900)
#
# Per-seat model: read from the "Model:" line of mandates/<seat>.md
# (single source of truth; run_seat.py refuses to start on a mismatch).
#
# Process model:
#   1. Lints the mandates (refuses to start if any names track-specific detail).
#   2. Starts "opencode serve", waits until it answers (several health paths,
#      falling back to "port is open").
#   3. Starts one run_seat.py per seat -> logs/<seat>.log; records
#      logs/started_at and logs/seat_models.txt.
#   4. Startup gate: every seat must still be alive after ~15 s, otherwise the
#      script exits non-zero BEFORE you send the dispatch.
#   5. Watchdog: if a seat process dies, restart it (up to MAX_RESTARTS) and log
#      the event to logs/events.log. This is operator-level process supervision;
#      it sends nothing to the room.
#   6. On SIGTERM/SIGINT/EXIT kills only our own child processes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_ROOT="$SCRIPT_DIR"
cd "$FACTORY_ROOT"

LOGS_DIR="$FACTORY_ROOT/logs"
SRC_DIR="$FACTORY_ROOT/src"
PID_DIR="$LOGS_DIR/pids"
EVENTS="$LOGS_DIR/events.log"
OC_PORT=4096
SEATS=(foreman smith inspector stresser)
MAX_RESTARTS="${MAX_RESTARTS:-3}"

# ── helpers ────────────────────────────────────────────────────────────────

die() { echo "ERROR: $*" >&2; exit 1; }
event() { echo "$(date -u +%FT%TZ) $*" | tee -a "$EVENTS" >&2; }

port_in_use() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        # single awk consumer (no early-exit grep -q => no SIGPIPE under pipefail)
        ss -tlnH 2>/dev/null | awk -v pat=":${port}\$" '$4 ~ pat {f=1} END {exit !f}'
    else
        python3 -c "
import socket, sys
try:
    s = socket.create_connection(('127.0.0.1', ${port}), timeout=0.5); s.close(); sys.exit(0)
except Exception: sys.exit(1)" 2>/dev/null
    fi
}

check_not_running() {
    local pidfile="$PID_DIR/${1}.pid"
    if [[ -f "$pidfile" ]]; then
        local old_pid; old_pid="$(cat "$pidfile")"
        if kill -0 "$old_pid" 2>/dev/null; then
            die "Seat '$1' is already running (PID $old_pid). Run stop-factory.sh first."
        else
            rm -f "$pidfile"
        fi
    fi
}

# ── pre-flight ──────────────────────────────────────────────────────────────

[[ -f "$FACTORY_ROOT/.env" ]] && { set -a; source "$FACTORY_ROOT/.env"; set +a; }

: "${RESULT_REPO:?RESULT_REPO must be set to the absolute path of the result git repository}"
[[ "$RESULT_REPO" == /* ]] || die "RESULT_REPO must be an absolute path: $RESULT_REPO"
[[ -d "$RESULT_REPO" ]] || die "RESULT_REPO does not exist: $RESULT_REPO"
[[ -d "$RESULT_REPO/.git" ]] || die "RESULT_REPO is not a git repository (no .git found): $RESULT_REPO. Run ./bootstrap-repo.sh $RESULT_REPO first."
[[ ! -f "$RESULT_REPO/.git/index.lock" ]] || die "Stale git lock detected: $RESULT_REPO/.git/index.lock. Remove it if no other git process is active."
[[ -n "${FEATHERLESS_API_KEY:-}" ]] || die "FEATHERLESS_API_KEY is empty (set it in .env)."
[[ -f "$FACTORY_ROOT/agent_config.yaml" ]] || die "agent_config.yaml missing (see FACTORY.md, Step 6)."
BRANCH="$(git -C "$RESULT_REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo "[factory] Target repo: $RESULT_REPO (branch: $BRANCH)"

OPENCODE_BIN="$(command -v opencode 2>/dev/null)" || die "opencode not found on PATH"
command -v uv >/dev/null 2>&1 || die "uv not found on PATH"
FACTORY_PYTHON="$FACTORY_ROOT/.venv/bin/python"
[[ -x "$FACTORY_PYTHON" ]] || die "factory virtualenv python not found: $FACTORY_PYTHON. Run uv sync first."

mkdir -p "$LOGS_DIR" "$PID_DIR"

echo "[factory] Linting mandates …"
"$FACTORY_PYTHON" "$SRC_DIR/lint_mandates.py" || die "mandates name track-specific detail (disqualifying). Fix them first."

# Resolve each seat's model from its mandate (fails early on a missing Model: line)
declare -A SEAT_MODEL
: > "$LOGS_DIR/seat_models.txt"
for seat in "${SEATS[@]}"; do
    SEAT_MODEL[$seat]="$("$FACTORY_PYTHON" "$SRC_DIR/run_seat.py" --model-of "$seat")" \
        || die "cannot resolve model for seat '$seat'"
    echo "$seat ${SEAT_MODEL[$seat]}" | tee -a "$LOGS_DIR/seat_models.txt"
done

for seat in "${SEATS[@]}"; do check_not_running "$seat"; done
port_in_use "$OC_PORT" && die "Something is already listening on port $OC_PORT. Is opencode serve already running?"

echo "$$" > "$PID_DIR/factory.pid"
: > "$EVENTS"

# ── cleanup on exit ─────────────────────────────────────────────────────────

OC_PID=""
declare -A PIDS
cleanup() {
    trap - EXIT INT TERM
    echo "[factory] Shutting down…"
    for seat in "${SEATS[@]}"; do
        [[ -n "${PIDS[$seat]:-}" ]] && kill "${PIDS[$seat]}" 2>/dev/null || true
        rm -f "$PID_DIR/${seat}.pid"
    done
    [[ -n "$OC_PID" ]] && kill "$OC_PID" 2>/dev/null || true
    rm -f "$PID_DIR/opencode.pid" "$PID_DIR/factory.pid"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# ── start opencode server ────────────────────────────────────────────────────

echo "[factory] Starting opencode serve on 127.0.0.1:$OC_PORT …"
# Run from FACTORY_ROOT, never from the result repo (so no result-repo config is read)
"$OPENCODE_BIN" serve --hostname=127.0.0.1 --port="$OC_PORT" >"$LOGS_DIR/opencode.log" 2>&1 &
OC_PID=$!
echo "$OC_PID" > "$PID_DIR/opencode.pid"

ready=0
for i in $(seq 1 30); do
    for path in /global/health /api/health /health; do
        if curl -sf "http://127.0.0.1:${OC_PORT}${path}" >/dev/null 2>&1; then ready=1; break 2; fi
    done
    kill -0 "$OC_PID" 2>/dev/null || { tail -20 "$LOGS_DIR/opencode.log" >&2; die "opencode exited during startup (see logs/opencode.log)"; }
    sleep 1
done
if [[ $ready -eq 1 ]]; then
    echo "[factory] opencode ready."
elif port_in_use "$OC_PORT"; then
    echo "[factory] WARN: no health path answered, but port $OC_PORT is open; continuing." >&2
else
    die "opencode did not become ready in 30s; see logs/opencode.log"
fi

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$LOGS_DIR/started_at"
echo "[factory] started_at: $(cat "$LOGS_DIR/started_at")"

# ── seats ────────────────────────────────────────────────────────────────────

start_seat() {
    local seat="$1"
    RESULT_REPO="$RESULT_REPO" "$FACTORY_PYTHON" "$SRC_DIR/run_seat.py" "$seat" "${SEAT_MODEL[$seat]}" \
        >>"$LOGS_DIR/${seat}.log" 2>&1 &
    PIDS[$seat]=$!
    echo "${PIDS[$seat]}" > "$PID_DIR/${seat}.pid"
}

for seat in "${SEATS[@]}"; do
    : > "$LOGS_DIR/${seat}.log"
    start_seat "$seat"
    echo "[factory] '$seat' started (PID ${PIDS[$seat]}, model ${SEAT_MODEL[$seat]}) → logs/${seat}.log"
    sleep 0.5
done

# Startup gate: all seats must survive ~15 s (catches bad key / config / model mismatch)
for _ in 1 2 3 4 5; do
    sleep 3
    for seat in "${SEATS[@]}"; do
        if ! kill -0 "${PIDS[$seat]}" 2>/dev/null; then
            tail -15 "$LOGS_DIR/${seat}.log" >&2
            die "seat '$seat' died during startup (see logs/${seat}.log). Do NOT send the dispatch."
        fi
    done
done
event "startup-ok seats=${#SEATS[@]}"
echo "[factory] All ${#SEATS[@]} seats are up. Send the dispatch now. Watching for crashes (Ctrl-C or stop-factory.sh to stop)."

# ── watchdog ─────────────────────────────────────────────────────────────────

declare -A RESTARTS GAVE_UP
while true; do
    sleep 10 & wait $! || true
    if ! kill -0 "$OC_PID" 2>/dev/null; then
        event "FATAL opencode server died (see logs/opencode.log)"
        exit 1
    fi
    for seat in "${SEATS[@]}"; do
        [[ -n "${GAVE_UP[$seat]:-}" ]] && continue
        if ! kill -0 "${PIDS[$seat]}" 2>/dev/null; then
            n=$(( ${RESTARTS[$seat]:-0} + 1 )); RESTARTS[$seat]=$n
            if (( n > MAX_RESTARTS )); then
                event "GAVE-UP seat=$seat after $MAX_RESTARTS restarts"
                GAVE_UP[$seat]=1
            else
                event "RESTART seat=$seat attempt=$n/$MAX_RESTARTS"
                echo "----- restart #$n $(date -u +%FT%TZ) -----" >>"$LOGS_DIR/${seat}.log"
                start_seat "$seat"
            fi
        fi
    done
done
