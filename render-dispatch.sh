#!/usr/bin/env bash
# render-dispatch.sh — Render dispatch message for @Foreman.
#
# Usage:
#   ./render-dispatch.sh engineering [--task "Build API"] [--repo /abs/path]
#   ./render-dispatch.sh security    [--task "Audit auth module"]
#   ./render-dispatch.sh forensics   [--task "Fix segfault in worker"]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
[[ -x "$PYTHON_BIN" ]] || PYTHON_BIN="python3"

OUT="$("$PYTHON_BIN" "$SCRIPT_DIR/src/render_dispatch.py" "$@")"
printf '%s\n' "$OUT"

# Copy to clipboard if available
for tool in wl-copy "xclip -selection clipboard" pbcopy; do
    tool_bin="${tool%% *}"
    if command -v "$tool_bin" >/dev/null 2>&1; then
        printf '%s\n' "$OUT" | $tool && echo "[render] copied to clipboard" >&2
        break
    fi
done
