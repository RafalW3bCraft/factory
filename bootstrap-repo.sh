#!/usr/bin/env bash
# bootstrap-repo.sh — Initialise a fresh workspace/result repository for the Factory.
#
# Usage:
#   ./bootstrap-repo.sh <absolute-path>
#
# Creates <path> as a new git repository (branch: main) with:
#   - .gitignore that excludes secrets, logs, and build artifacts
#   - Language-neutral README.md project template with architecture & verification sections (H4)
#   - Clean initial commit
set -euo pipefail

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
# Refuse existing content, path aliases, and nested repositories before writes.
python3 - "$TARGET" <<'PY'
import subprocess
import sys
from pathlib import Path
target = Path(sys.argv[1])
if target.exists() or target.is_symlink():
    sys.exit("ERROR: target must be a new, nonexistent directory.")
if target.absolute() != target.resolve():
    sys.exit("ERROR: symlink or noncanonical paths are not allowed.")
parent = target.parent
if not parent.is_dir():
    sys.exit("ERROR: target parent must already exist.")
result = subprocess.run(["git", "-C", str(parent), "rev-parse", "--show-toplevel"], capture_output=True)
if result.returncode == 0:
    sys.exit("ERROR: refusing a nested repository inside an existing checkout.")
PY
mkdir -- "$TARGET"
git -C "$TARGET" init -b main

# .gitignore (comprehensive, polyglot & secrets)
cat > "$TARGET/.gitignore" <<'GITIGNORE'
# Secrets & credentials — never commit
.env
*.env
agent_config.yaml
opencode.json

# Build & packaging
dist/
build/
target/
bin/
obj/

# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Node / TypeScript
node_modules/
.npm/
.yarn/

# Rust / Go / C++
Cargo.lock
vendor/
*.o
*.a
*.so

# Logs & temp
*.log
logs/
tmp/
temp/

# OS metadata
.DS_Store
Thumbs.db
GITIGNORE

# Polyglot Project README.md (H4)
cat > "$TARGET/README.md" <<'README'
# Project Workspace

Target workspace engineered and verified autonomously by the Dark Factory band.

## Factory Team & Roles
- **@Foreman**: System Architecture, Task Planning, Threat Modeling & Coordination
- **@Smith**: Full-Stack Construction, Secure Coding, Test-Driven Development (TDD)
- **@Inspector**: Independent Review, Static Analysis (SAST), Security Audit & Code Forensics
- **@Stresser**: Adversarial Testing, Fuzzing, Dynamic Penetration & Crash Forensics

## Project Structure
```
.
├── src/            # Application source code
├── tests/          # Automated test suites (unit, integration, regression)
└── docs/           # Architecture designs, threat models, and milestone reports
```

## Verification
Follow the testing and verification commands defined in the Foreman dispatch.
README

# Initial commit
git -C "$TARGET" config core.pager cat
git -C "$TARGET" config user.name "factory-bootstrap"
git -C "$TARGET" config user.email "factory-bootstrap@factory.invalid"
git -C "$TARGET" add -- .gitignore README.md
git -C "$TARGET" -c core.hooksPath=/dev/null commit --no-gpg-sign -m "chore: bootstrap project repository for Dark Factory"

echo "[bootstrap] Done. Repository initialised at $TARGET"
echo "[bootstrap] Next: set RESULT_REPO=$TARGET in .env and run ./preflight.sh"
