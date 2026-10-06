#!/usr/bin/env bash
# render-dispatch.sh pocketful|toy [--stages N]
# Prints the resolved dispatch; also copies it to the clipboard if a tool exists.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT/.venv/bin/python"; [[ -x "$PY" ]] || PY=python3
OUT="$("$PY" "$ROOT/src/render_dispatch.py" "$@")"
printf '%s\n' "$OUT"
for c in wl-copy "xclip -selection clipboard" pbcopy; do
  if command -v "${c%% *}" >/dev/null 2>&1; then printf '%s\n' "$OUT" | $c && echo "[render] copied to clipboard" >&2; break; fi
done
