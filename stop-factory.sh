#!/usr/bin/env bash
# stop-factory.sh — cleanly stop factory processes started by start-factory.sh.
#
# Usage:
#   ./stop-factory.sh
#
# Hardening & Reliability Features:
#   - Kills only supervisor and seat processes recorded in logs/pids/ (R4).
#   - Checks /proc/<pid>/cmdline to eliminate PID-reuse race conditions (R4).
#   - Grace period with SIGTERM before escalating to SIGKILL (R4).
#   - Dynamic port lookup via OPENCODE_PORT (R5).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_ROOT="$SCRIPT_DIR"
PID_DIR="$FACTORY_ROOT/logs/pids"
OC_PORT="${OPENCODE_PORT:-4096}"

# Validate OPENCODE_PORT format
if ! [[ "$OC_PORT" =~ ^[0-9]+$ ]] || (( OC_PORT < 1024 || OC_PORT > 65535 )); then
    echo "[stop] WARN: Invalid OPENCODE_PORT '$OC_PORT'; defaulting to 4096." >&2
    OC_PORT=4096
fi

SEATS=(foreman smith inspector stresser)

kill_pid_file() {
    local name="$1"
    local pidfile="$PID_DIR/${name}.pid"
    if [[ -f "$pidfile" ]]; then
        local pid
        pid="$(cat "$pidfile" 2>/dev/null | tr -d '[:space:]')"
        if [[ ! "$pid" =~ ^[1-9][0-9]*$ ]] || (( pid <= 1 || pid == $$ )); then
            echo "[stop] Invalid or unsafe PID in '$pidfile'; removing."
            rm -f "$pidfile"
            return 0
        fi
        if kill -0 "$pid" 2>/dev/null; then
            # Safety: ensure process cmdline belongs to factory/opencode/python
            if [[ -f "/proc/$pid/cmdline" ]] && ! grep -qE "python|opencode|start-factory|run_seat" "/proc/$pid/cmdline" 2>/dev/null; then
                echo "[stop] PID $pid for '$name' does not match factory process; skipping."
                rm -f "$pidfile"
                return 0
            fi
            echo "[stop] Stopping '$name' (PID $pid)…"
            kill "$pid" 2>/dev/null || true
            # Wait up to 5s for clean exit
            for _ in $(seq 1 5); do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            # Escalation only if process survived grace period
            if kill -0 "$pid" 2>/dev/null; then
                echo "[stop] Escalating to SIGKILL for '$name' (PID $pid)…"
                kill -9 "$pid" 2>/dev/null || true
            fi
        else
            echo "[stop] '$name' (PID $pid) is not running."
        fi
        rm -f "$pidfile"
    else
        echo "[stop] No PID file for '$name'; skipping."
    fi
}

# Stop supervisor first so watchdog doesn't restart terminated seats
kill_pid_file "factory"

# Then stop individual seats
for seat in "${SEATS[@]}"; do
    kill_pid_file "$seat"
done

# Stop OpenCode server
kill_pid_file "opencode"

# Check if configured port is still bound by an orphaned opencode server
if command -v ss >/dev/null 2>&1; then
    if ss -tlnH 2>/dev/null | awk -v pat=":${OC_PORT}\$" '$4 ~ pat {f=1} END {exit !f}'; then
        echo "[stop] Port $OC_PORT is still in use. Checking for orphaned opencode serve…"
        pkill -f "opencode serve.*${OC_PORT}" 2>/dev/null || true
        sleep 1
    fi
fi

# Clean any leftover kill switch file
rm -f "$FACTORY_ROOT/factory.kill"

echo "[stop] Factory shutdown complete."
