#!/usr/bin/env bash
# start-factory.sh — start the OpenCode server and one run_seat.py per seat.
#
# Usage:   RESULT_REPO=/abs/path ./start-factory.sh
#
# Required env / .env:
#   RESULT_REPO          absolute path of the result git repository
#   FEATHERLESS_API_KEY  (loaded safely from .env if present)
# Optional:
#   OPENCODE_PORT        port to listen on (default: 4096)
#   MAX_RESTARTS         per-seat auto-restart budget in 10-minute window (default: 3)
#   MISSION_TIMEOUT_S    mission wall-clock timeout in seconds (default: 14400 = 4h)
#   TURN_TIMEOUT_S       per-turn timeout passed to the adapter (default: 900)
#
# Hardening & Security Features:
#   - Safe KEY=VALUE .env parsing without arbitrary shell execution (S3).
#   - OpenCode server authentication via OPENCODE_SERVER_PASSWORD (S5).
#   - Sanitized opencode serve environment: FEATHERLESS_API_KEY is not passed to child shells (S2).
#   - Per-seat credential isolation: each seat receives only its own credentials (S2).
#   - Run-isolated log directories under logs/runs/<run_id>/ with retention and latest symlink (R3).
#   - Windowed restart watchdog with backoff and fail-fast termination on Foreman crash (R1).
#   - Mission-level wall-clock timeout and file-based kill switch factory.kill (R2).
#   - Process group tracking for clean child termination without PID-reuse race (R4).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_ROOT="$SCRIPT_DIR"
cd "$FACTORY_ROOT"

# Load safe env parser (S3)
# shellcheck source=scripts/load_env.sh disable=SC1091
source "$FACTORY_ROOT/scripts/load_env.sh"

LOGS_DIR="$FACTORY_ROOT/logs"
PID_DIR="$LOGS_DIR/pids"
SRC_DIR="$FACTORY_ROOT/src"
OC_PORT="${OPENCODE_PORT:-4096}"
SEATS=(foreman smith inspector stresser)
MAX_RESTARTS="${MAX_RESTARTS:-3}"
MISSION_TIMEOUT_S="${MISSION_TIMEOUT_S:-14400}"
RESTART_WINDOW_S=600

# ── helpers ────────────────────────────────────────────────────────────────

die() { echo "ERROR: $*" >&2; exit 1; }

# Port validation
if ! [[ "$OC_PORT" =~ ^[0-9]+$ ]] || (( OC_PORT < 1024 || OC_PORT > 65535 )); then
    die "Invalid OPENCODE_PORT: '$OC_PORT'. Must be an integer between 1024 and 65535."
fi

# Initialize run-isolated logs (R3)
RUN_ID="$(date -u +%Y%m%d_%H%M%SZ)"
RUN_LOG_DIR="$LOGS_DIR/runs/$RUN_ID"
mkdir -p "$RUN_LOG_DIR" "$PID_DIR"
ln -sfn "$RUN_LOG_DIR" "$LOGS_DIR/latest"

EVENTS="$RUN_LOG_DIR/events.log"
: > "$EVENTS"

# Retention policy: prune runs older than the newest 20 runs
find "$LOGS_DIR/runs" -mindepth 1 -maxdepth 1 -type d | sort | head -n -20 | xargs rm -rf 2>/dev/null || true

event() { echo "$(date -u +%FT%TZ) $*" | tee -a "$EVENTS" >&2; }

port_in_use() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
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
    local name="$1"
    local pidfile="$PID_DIR/${name}.pid"
    if [[ -f "$pidfile" ]]; then
        local old_pid
        old_pid="$(cat "$pidfile" 2>/dev/null | tr -d '[:space:]')"
        if [[ "$old_pid" =~ ^[1-9][0-9]*$ ]] && (( old_pid > 1 )) && kill -0 "$old_pid" 2>/dev/null; then
            die "Process '$name' is already running (PID $old_pid). Run stop-factory.sh first."
        else
            rm -f "$pidfile"
        fi
    fi
}

# ── pre-flight ──────────────────────────────────────────────────────────────

check_not_running "factory"

load_env_safe "$FACTORY_ROOT/.env"

: "${RESULT_REPO:?RESULT_REPO must be set to the absolute path of the result git repository}"
[[ "$RESULT_REPO" == /* ]] || die "RESULT_REPO must be an absolute path: $RESULT_REPO"
[[ -d "$RESULT_REPO" ]] || die "RESULT_REPO does not exist: $RESULT_REPO"
[[ -d "$RESULT_REPO/.git" ]] || die "RESULT_REPO is not a git repository (no .git found): $RESULT_REPO. Run ./bootstrap-repo.sh $RESULT_REPO first."
[[ ! -f "$RESULT_REPO/.git/index.lock" ]] || die "Stale git lock detected: $RESULT_REPO/.git/index.lock. Remove it if no other git process is active."
[[ -n "${FEATHERLESS_API_KEY:-}" ]] || die "FEATHERLESS_API_KEY is empty (set it in .env)."

AGENT_CFG="$FACTORY_ROOT/agent_config.yaml"
[[ -f "$AGENT_CFG" ]] || die "agent_config.yaml missing. Copy agent_config.example.yaml to agent_config.yaml and configure seat credentials."

BRANCH="$(git -C "$RESULT_REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo "[factory] Target repo: $RESULT_REPO (branch: $BRANCH)"
echo "[factory] Run ID: $RUN_ID (logs: logs/runs/$RUN_ID)"

OPENCODE_BIN="$(command -v opencode 2>/dev/null)" || die "opencode not found on PATH"
command -v uv >/dev/null 2>&1 || die "uv not found on PATH"
FACTORY_PYTHON="$FACTORY_ROOT/.venv/bin/python"
[[ -x "$FACTORY_PYTHON" ]] || die "factory virtualenv python not found: $FACTORY_PYTHON. Run uv sync first."

echo "[factory] Validating mandates …"
"$FACTORY_PYTHON" "$SRC_DIR/lint_mandates.py" || die "Mandates verification failed. Fix issues reported by lint_mandates.py first."

# Generate OpenCode server password if not already set (S5)
OPENCODE_SERVER_PASSWORD="${OPENCODE_SERVER_PASSWORD:-$("$FACTORY_PYTHON" -c 'import secrets; print(secrets.token_hex(16))')}"
export OPENCODE_SERVER_PASSWORD

# Resolve each seat's model from its mandate
declare -A SEAT_MODEL
: > "$RUN_LOG_DIR/seat_models.txt"
for seat in "${SEATS[@]}"; do
    SEAT_MODEL[$seat]="$("$FACTORY_PYTHON" "$SRC_DIR/run_seat.py" --model-of "$seat")" \
        || die "cannot resolve model for seat '$seat'"
    echo "$seat ${SEAT_MODEL[$seat]}" | tee -a "$RUN_LOG_DIR/seat_models.txt"
done

check_not_running "factory"
check_not_running "opencode"
for seat in "${SEATS[@]}"; do check_not_running "$seat"; done
port_in_use "$OC_PORT" && die "Something is already listening on port $OC_PORT. Is opencode serve already running?"

echo "$$" > "$PID_DIR/factory.pid"

# ── cleanup on exit ─────────────────────────────────────────────────────────

OC_PID=""
declare -A PIDS
cleanup() {
    trap - EXIT INT TERM
    echo "[factory] Shutting down factory processes…"
    for seat in "${SEATS[@]}"; do
        if [[ -n "${PIDS[$seat]:-}" ]]; then
            kill "${PIDS[$seat]}" 2>/dev/null || true
        fi
        rm -f "$PID_DIR/${seat}.pid"
    done
    if [[ -n "$OC_PID" ]]; then
        kill "$OC_PID" 2>/dev/null || true
    fi
    rm -f "$PID_DIR/opencode.pid" "$PID_DIR/factory.pid" "$FACTORY_ROOT/factory.kill"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# ── start opencode server ────────────────────────────────────────────────────

echo "[factory] Starting authenticated opencode serve on 127.0.0.1:$OC_PORT …"
# S2: Unset FEATHERLESS_API_KEY from server env so child shells cannot print it
# S5: OPENCODE_SERVER_PASSWORD is set for Basic Auth
env -u FEATHERLESS_API_KEY \
    OPENCODE_SERVER_PASSWORD="$OPENCODE_SERVER_PASSWORD" \
    "$OPENCODE_BIN" serve --hostname=127.0.0.1 --port="$OC_PORT" >"$RUN_LOG_DIR/opencode.log" 2>&1 &
OC_PID=$!
echo "$OC_PID" > "$PID_DIR/opencode.pid"

ready=0
for _ in $(seq 1 30); do
    for path in /global/health /api/health /health; do
        if curl -sf -u "opencode:${OPENCODE_SERVER_PASSWORD}" "http://127.0.0.1:${OC_PORT}${path}" >/dev/null 2>&1; then
            ready=1
            break 2
        fi
    done
    if ! kill -0 "$OC_PID" 2>/dev/null; then
        tail -20 "$RUN_LOG_DIR/opencode.log" >&2
        die "opencode exited during startup (see logs/latest/opencode.log)"
    fi
    sleep 1
done

if [[ $ready -eq 1 ]]; then
    echo "[factory] opencode server ready and authenticated."
elif port_in_use "$OC_PORT"; then
    echo "[factory] WARN: health endpoint did not answer, but port $OC_PORT is open; continuing." >&2
else
    die "opencode did not become ready in 30s; see logs/latest/opencode.log"
fi

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUN_LOG_DIR/started_at"
echo "[factory] started_at: $(cat "$RUN_LOG_DIR/started_at")"

# ── seats ────────────────────────────────────────────────────────────────────

start_seat() {
    local seat="$1"
    # S2: Extract ONLY this seat's credentials so no cross-seat leakage occurs
    local seat_creds
    seat_creds="$("$FACTORY_PYTHON" -c "
from band.config import load_agent_config
try:
    aid, key = load_agent_config('$seat', config_path='$AGENT_CFG')
    print(f'{aid} {key}')
except Exception:
    pass
" 2>/dev/null || echo '')"

    local agent_id="${seat_creds%% *}"
    local api_key="${seat_creds#* }"

    BAND_AGENT_ID="$agent_id" \
    BAND_API_KEY="$api_key" \
    OPENCODE_BASE_URL="http://127.0.0.1:$OC_PORT" \
    OPENCODE_SERVER_PASSWORD="$OPENCODE_SERVER_PASSWORD" \
    RESULT_REPO="$RESULT_REPO" \
    "$FACTORY_PYTHON" "$SRC_DIR/run_seat.py" "$seat" "${SEAT_MODEL[$seat]}" \
        >>"$RUN_LOG_DIR/${seat}.log" 2>&1 &

    PIDS[$seat]=$!
    echo "${PIDS[$seat]}" > "$PID_DIR/${seat}.pid"
}

for seat in "${SEATS[@]}"; do
    : > "$RUN_LOG_DIR/${seat}.log"
    start_seat "$seat"
    echo "[factory] '$seat' started (PID ${PIDS[$seat]}, model ${SEAT_MODEL[$seat]}) → logs/latest/${seat}.log"
    sleep 0.5
done

# Startup gate: all seats must survive ~15 s
for _ in 1 2 3 4 5; do
    sleep 3
    for seat in "${SEATS[@]}"; do
        if ! kill -0 "${PIDS[$seat]}" 2>/dev/null; then
            tail -15 "$RUN_LOG_DIR/${seat}.log" >&2
            die "seat '$seat' died during startup (see logs/latest/${seat}.log). Do NOT send the dispatch."
        fi
    done
done

event "startup-ok seats=${#SEATS[@]} run_id=$RUN_ID"
echo "[factory] All ${#SEATS[@]} seats are up. Send the dispatch now. Watching for crashes."
echo "[factory] Kill switch: touch factory.kill or run ./stop-factory.sh"

# ── watchdog with windowed backoff & fail-fast (R1, R2) ───────────────────────

declare -A RESTART_TIMESTAMPS GAVE_UP
START_EPOCH="$(date +%s)"

while true; do
    sleep 10 & wait $! || true

    # R2: Check mission wall-clock timeout
    CURRENT_EPOCH="$(date +%s)"
    ELAPSED=$(( CURRENT_EPOCH - START_EPOCH ))
    if (( ELAPSED > MISSION_TIMEOUT_S )); then
        event "FATAL mission wall-clock timeout reached (${MISSION_TIMEOUT_S}s); terminating"
        exit 1
    fi

    # R2: Check file-based kill switch
    if [[ -f "$FACTORY_ROOT/factory.kill" ]]; then
        event "INFO kill switch factory.kill detected; terminating cleanly"
        exit 0
    fi

    if ! kill -0 "$OC_PID" 2>/dev/null; then
        event "FATAL opencode server died (see logs/latest/opencode.log)"
        exit 1
    fi

    for seat in "${SEATS[@]}"; do
        [[ -n "${GAVE_UP[$seat]:-}" ]] && continue

        if ! kill -0 "${PIDS[$seat]}" 2>/dev/null; then
            # Clean expired timestamps outside sliding window
            local_now="$(date +%s)"
            raw_history="${RESTART_TIMESTAMPS[$seat]:-}"
            new_history=""
            count=0
            for ts in $raw_history; do
                if (( local_now - ts < RESTART_WINDOW_S )); then
                    new_history="$new_history $ts"
                    count=$(( count + 1 ))
                fi
            done

            count=$(( count + 1 ))
            new_history="$new_history $local_now"
            RESTART_TIMESTAMPS[$seat]="$new_history"

            if (( count > MAX_RESTARTS )); then
                event "FATAL seat=$seat exhausted restart budget ($MAX_RESTARTS restarts within ${RESTART_WINDOW_S}s)"
                GAVE_UP[$seat]=1
                # R1 Fail-fast: If Foreman or any critical seat exhausts budget, fail fast
                if [[ "$seat" == "foreman" ]]; then
                    event "FATAL Lead orchestrator (@Foreman) failed; aborting mission"
                    exit 1
                fi
            else
                event "RESTART seat=$seat attempt=$count/$MAX_RESTARTS window=${RESTART_WINDOW_S}s"
                echo "----- restart #$count $(date -u +%FT%TZ) -----" >>"$RUN_LOG_DIR/${seat}.log"
                # Exponential backoff (2^count seconds)
                backoff_s=$(( 2 ** count ))
                sleep "$backoff_s"
                start_seat "$seat"
            fi
        fi
    done
done
