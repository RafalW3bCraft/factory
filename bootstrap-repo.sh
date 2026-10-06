#!/usr/bin/env bash
# bootstrap-repo.sh — Initialise a fresh workspace/result repository for the Factory.
#
# Usage:
#   ./bootstrap-repo.sh <absolute-path>
#
# Creates <path> as a new git repository (branch: main) with:
#   - mandates/ copied from factory/mandates/
#   - .gitignore that excludes secrets and build artifacts
#   - README.md project template with architecture and test sections
#   - Clean initial commit
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_ROOT="$SCRIPT_DIR"

if [[ $# -ne 1 || "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: bootstrap-repo.sh <absolute-path>"
    echo ""
    echo "Initialises a clean workspace repository at <absolute-path>."
    echo "The path must be absolute. The directory must not already be a git repo."
    exit 0
fi

TARGET="$1"
[[ "$TARGET" == /* ]] || { echo "ERROR: path must be absolute: $TARGET" >&2; exit 1; }

if [[ -d "$TARGET/.git" ]]; then
    echo "ERROR: $TARGET is already a git repository." >&2
    exit 1
fi

echo "[bootstrap] Creating clean repository at $TARGET …"
mkdir -p "$TARGET/mandates"
git -C "$TARGET" init -b main

# Copy mandates from factory
MANDATES_SRC="$FACTORY_ROOT/mandates"
if [[ -d "$MANDATES_SRC" ]] && compgen -G "$MANDATES_SRC/*.md" > /dev/null 2>&1; then
    cp "$MANDATES_SRC/"*.md "$TARGET/mandates/"
    echo "[bootstrap] Copied mandates from $MANDATES_SRC."
else
    echo "[bootstrap] WARNING: no mandate files found in $MANDATES_SRC"
fi

# .gitignore
cat > "$TARGET/.gitignore" <<'GITIGNORE'
# Secrets — never commit credentials or keys
.env
*.env
agent_config.yaml
opencode.json

# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node / JS
node_modules/
dist/
build/

# Logs & temp
*.log
logs/
tmp/

# OS
.DS_Store
Thumbs.db
GITIGNORE

# Project README.md
cat > "$TARGET/README.md" <<'README'
# Project Workspace

Managed and developed autonomously by the Dark Factory band.

## Factory Team & Roles
- **@Foreman**: System Architecture, Task Planning, Threat Modeling & Coordination
- **@Smith**: Full-Stack Construction, Secure Coding, Test-Driven Development (TDD)
- **@Inspector**: Independent Review, Static Analysis (SAST), Security Audit & Code Forensics
- **@Stresser**: Adversarial Testing, Fuzzing, Dynamic Penetration & Crash Forensics

## Structure
```
.
├── mandates/       # Operating instructions and models for the 4 seats
├── src/            # Core application source code
├── tests/          # Automated test suites (unit, integration, regression)
└── docs/           # Architecture decisions, threat models, and incident reports
```

## Running Checks
```bash
# Execute local test suite
pytest -v

# Run security and linter checks
ruff check .
```
README

# Initial commit
git -C "$TARGET" config user.name "factory-bootstrap"
git -C "$TARGET" config user.email "factory-bootstrap@factory.invalid"
git -C "$TARGET" add .
git -C "$TARGET" commit -m "chore: bootstrap project repository for Dark Factory"

echo "[bootstrap] Done. Repository initialised at $TARGET"
echo "[bootstrap] Next: set RESULT_REPO=$TARGET in .env and run ./preflight.sh"
