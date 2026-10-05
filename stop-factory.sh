#!/usr/bin/env bash
# stop-factory.sh — stop factory processes started by start-factory.sh.
#
# Usage:
#   ./stop-factory.sh
#
# Kills only the opencode server and seat processes whose PIDs were written
# to logs/pids/ by start-factory.sh. Never kills arbitrary processes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_ROOT="$SCRIPT_DIR"
PID_DIR="$FACTORY_ROOT/logs/pids"

SEATS=(foreman smith inspector stresser)

kill_pid_file() {
    local name="$1"
    local pidfile="$PID_DIR/${name}.pid"
    if [[ -f "$pidfile" ]]; then
        local pid
        pid="$(cat "$pidfile")"
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
                kill -0 "$pid" 2>/dev/null || break
                sleep 1
            done
            kill -9 "$pid" 2>/dev/null || true
        else
            echo "[stop] '$name' (PID $pid) is not running."
        fi
        rm -f "$pidfile"
    else
        echo "[stop] No PID file for '$name'; skipping."
    fi
}

for seat in "${SEATS[@]}"; do
    kill_pid_file "$seat"
done
kill_pid_file "opencode"
kill_pid_file "factory"

# Check if port 4096 is still bound by an orphaned opencode server
if command -v ss >/dev/null 2>&1; then
    if ss -tlnH 2>/dev/null | awk '{print $4}' | grep -q ":4096$"; then
        echo "[stop] Port 4096 is still in use. Checking for orphaned opencode serve…"
        pkill -f "opencode serve.*4096" 2>/dev/null || true
        sleep 1
    fi
fi

echo "[stop] Done."
