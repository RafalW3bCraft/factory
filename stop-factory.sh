#!/usr/bin/env bash
# Stop only processes authenticated by private kernel-identity records.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${FACTORY_STATE_DIR:-$SCRIPT_DIR/logs}"
PID_DIR="$STATE_DIR/pids"
FACTORY_PYTHON="${FACTORY_PYTHON:-python3}"
[[ ! -L "$STATE_DIR" && ! -L "$PID_DIR" ]] || { echo 'ERROR: symlink state directories are forbidden.' >&2; exit 1; }
for name in factory foreman smith inspector stresser opencode; do
    if [[ -f "$PID_DIR/$name.identity.json" ]]; then
        "$FACTORY_PYTHON" "$SCRIPT_DIR/src/factory/process_identity.py" stop "$PID_DIR/$name.identity.json"
    elif [[ -f "$PID_DIR/$name.pid" ]]; then
        echo "[stop] Invalid or unsafe PID without ownership evidence for '$name'; refusing to signal."
    fi
    rm -f -- "$PID_DIR/$name.pid"
done
echo '[stop] Factory shutdown complete.'
