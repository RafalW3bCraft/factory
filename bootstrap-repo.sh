#!/usr/bin/env bash
# bootstrap-repo.sh — initialise a fresh result repository.
#
# Usage:
#   ./bootstrap-repo.sh <absolute-path>
#
# Creates <path> as a new git repo (branch: main) with:
#   - mandates/ copied from factory/mandates/
#   - README.md skeleton
#   - FACTORY.md skeleton
#   - .gitignore that excludes secrets and Python artifacts
#
# Does NOT create any stage-* directories (those are built by the seats).
# Safe to run on a path that does not yet exist.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_ROOT="$SCRIPT_DIR"

# ── args ─────────────────────────────────────────────────────────────────────

if [[ $# -ne 1 || "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: bootstrap-repo.sh <absolute-path>"
    echo ""
    echo "Initialises a fresh submission repository at <absolute-path>."
    echo "The path must be absolute. The directory must not already be a git repo."
    exit 0
fi

TARGET="$1"
[[ "$TARGET" == /* ]] || { echo "ERROR: path must be absolute: $TARGET" >&2; exit 1; }

if [[ -d "$TARGET/.git" ]]; then
    echo "ERROR: $TARGET is already a git repository. Remove it first or choose a different path." >&2
    exit 1
fi

# ── create repo ──────────────────────────────────────────────────────────────

echo "[bootstrap] Creating repo at $TARGET …"
mkdir -p "$TARGET/mandates"
git -C "$TARGET" init -b main

# Copy mandates
if [[ -d "$FACTORY_ROOT/mandates" ]] && compgen -G "$FACTORY_ROOT/mandates/*.md" > /dev/null 2>&1; then
    cp "$FACTORY_ROOT/mandates/"*.md "$TARGET/mandates/"
    echo "[bootstrap] Mandates copied."
else
    echo "[bootstrap] WARNING: no mandate files found in $FACTORY_ROOT/mandates/ — copy them manually."
fi

# .gitignore — exclude secrets and build artifacts
cat > "$TARGET/.gitignore" <<'GITIGNORE'
# Secrets — keep outside any repo that is pushed
.env
*.env
agent_config.yaml
opencode.json

# Python
__pycache__/
*.py[oc]
.venv/
*.egg-info/

# Node / JS
node_modules/
dist/
build/

# OS
.DS_Store
Thumbs.db
GITIGNORE

# README.md — copy from templates if available, else use fallback
if [[ -f "$FACTORY_ROOT/templates/README.md" ]]; then
    cp "$FACTORY_ROOT/templates/README.md" "$TARGET/README.md"
    echo "[bootstrap] Copied README.md from templates."
else
    cat > "$TARGET/README.md" <<'README'
# Pocketful Dark Factory — Submission

**Track:** pocketful  
**Team:** <!-- add team name -->  
**Submission repo:** <!-- add GitHub URL -->

## What this repository contains

| Path | Purpose |
|---|---|
| `FACTORY.md` | Factory design, setup instructions, costs, failure handling |
| `mandates/` | One mandate per Band seat |
| `room.json` | Full Band room download (added after the run) |
| `stage-1/` | Stage 1 service: API built by the band |
| `stage-2/` | Stage 2 service: UI + authorizations |
| `stage-3/` | Stage 3 service: statements + corrections |
| `stage-4/` | Stage 4 service: refunds + batch corrections |

## Quickstart (harness check)

```sh
python -m harness check . --track pocketful
python -m harness run --track pocketful --repo . --all --mode isolated --out ../checks/final
```

## Factory

See `FACTORY.md` for full instructions on standing this factory up from scratch.
README
fi

# FACTORY.md — copy from templates if available, else use fallback
if [[ -f "$FACTORY_ROOT/templates/FACTORY.md" ]]; then
    cp "$FACTORY_ROOT/templates/FACTORY.md" "$TARGET/FACTORY.md"
    echo "[bootstrap] Copied FACTORY.md from templates."
else
    cat > "$TARGET/FACTORY.md" <<'FACTORY'
# FACTORY.md

<!-- Copy and complete this from factory/templates/FACTORY.md after the run. -->

## Overview

## Seats

| Role key | Band display name | Harness | Model | Setup |
|---|---|---|---|---|

## Stand it up from scratch

## Design choices and why

## What we tried that failed

_(append-only log)_

## Measured time and model spend per stage

| Stage | Wall-clock start | Wall-clock end | Duration | Model spend |
|---|---|---|---|---|

How to measure:
- Wall-clock: `cat logs/started_at` for start; room.json timestamps for end.
- Model spend: Featherless subscription page (filter by date).

## How the factory catches and recovers from bad work

## Limitations
FACTORY
fi

# Initial commit
git -C "$TARGET" config user.name "factory-bootstrap"
git -C "$TARGET" config user.email "factory-bootstrap@factory.invalid"
git -C "$TARGET" add .
git -C "$TARGET" commit -m "chore: bootstrap result repository"

echo "[bootstrap] Done. Repository initialised at $TARGET"
echo "[bootstrap] Next: set RESULT_REPO=$TARGET and run start-factory.sh"
