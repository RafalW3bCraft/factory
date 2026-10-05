#!/usr/bin/env bash
# preflight.sh — validate a result repository before submission.
#
# Usage:
#   ./preflight.sh <repo-path>
#
# What it does:
#   1. Fresh-clones <repo-path> (if it is a local path) into a temp dir,
#      or uses a remote URL via git clone.
#   2. Runs "python -m harness check <clone> --track pocketful".
#   3. Runs "python -m harness run --track pocketful --repo <clone>
#             --all --mode isolated --out <new dir under ~/band-work/checks>".
#   4. Asserts structural rules (no .git inside stage dirs, no submodules,
#      no symlinks, Dockerfile + RUN.md per stage, room.json present,
#      no credential patterns, mandate header lines present).
#
# Requires: git, python (with harness installed), docker daemon accessible.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKS_BASE="${HOME}/band-work/checks"

# Locate the harness venv. Try:
# 1. Sibling dark-factory-wearedevs/ next to this factory dir
# 2. HARNESS_REPO env var (override)
# 3. ~/band-work/dark-factory-wearedevs (conventional location)
if [[ -n "${HARNESS_REPO:-}" ]]; then
    : # use env var as-is
elif HARNESS_REPO="$(cd "$SCRIPT_DIR/../dark-factory-wearedevs" 2>/dev/null && pwd)"; then
    : # found sibling
elif [[ -d "$HOME/band-work/dark-factory-wearedevs" ]]; then
    HARNESS_REPO="$HOME/band-work/dark-factory-wearedevs"
else
    HARNESS_REPO=""
fi

# ── helpers ──────────────────────────────────────────────────────────────────

die()  { echo "FAIL: $*" >&2; FAILED=1; }
info() { echo "  OK: $*"; }
warn() { echo "WARN: $*"; }

FAILED=0

# ── args ─────────────────────────────────────────────────────────────────────

if [[ $# -ne 1 || "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: preflight.sh <repo-path-or-url>"
    echo ""
    echo "Validates the result repository before submission."
    echo "Pass either a local absolute path or a https://github.com/... URL."
    exit 0
fi

REPO_ARG="$1"
TMPDIR_BASE="$(mktemp -d)"
CLONE_DIR="$TMPDIR_BASE/clone"

cleanup() { rm -rf "$TMPDIR_BASE"; }
trap cleanup EXIT

# ── clone ────────────────────────────────────────────────────────────────────

echo "[preflight] Cloning repository …"
if [[ "$REPO_ARG" == http* || "$REPO_ARG" == git@* ]]; then
    git clone --depth=1 "$REPO_ARG" "$CLONE_DIR"
else
    # Local path: fresh clone proves nothing is gitignored/untracked
    [[ -d "$REPO_ARG/.git" ]] || { echo "ERROR: $REPO_ARG is not a git repository." >&2; exit 1; }
    git clone "$REPO_ARG" "$CLONE_DIR"
fi
LATEST_REV="$(git -C "$CLONE_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")"
COMMIT_COUNT="$(git -C "$CLONE_DIR" rev-list --count HEAD 2>/dev/null || echo "0")"
info "Clone succeeded: revision $LATEST_REV ($COMMIT_COUNT commits in history)."

if [[ -d "$REPO_ARG/.git" ]]; then
    REMOTE_URL="$(git -C "$REPO_ARG" remote get-url origin 2>/dev/null || true)"
    if [[ -n "$REMOTE_URL" ]]; then
        info "Configured git remote: $REMOTE_URL"
    else
        warn "No 'origin' remote configured on $REPO_ARG (remember to push to a public GitHub repo)."
    fi
fi

# ── harness check ────────────────────────────────────────────────────────────

echo ""
echo "[preflight] Running harness check …"

if [[ -n "$HARNESS_REPO" && -x "$HARNESS_REPO/.venv/bin/python" ]]; then
    HARNESS_PYTHON="$HARNESS_REPO/.venv/bin/python"
else
    # Fall back: find any python that has harness installed
    HARNESS_PYTHON="python"
    for candidate in python3 python3.12 python3.13; do
        if command -v "$candidate" >/dev/null 2>&1 && \
           "$candidate" -c 'import harness' 2>/dev/null; then
            HARNESS_PYTHON="$candidate"; break
        fi
    done
fi
echo "[preflight] Using python: $HARNESS_PYTHON (harness: ${HARNESS_REPO:-not found})"
[[ -n "$HARNESS_REPO" ]] && export PYTHONPATH="${HARNESS_REPO}:${PYTHONPATH:-}"

if "$HARNESS_PYTHON" -m harness check "$CLONE_DIR" --track pocketful; then
    info "harness check passed."
else
    die "harness check FAILED."
fi

# ── structural assertions ─────────────────────────────────────────────────────

echo ""
echo "[preflight] Running structural assertions …"

# 1. No .git directory inside stage-* folders
for stage_dir in "$CLONE_DIR"/stage-*/; do
    [[ -d "$stage_dir" ]] || continue
    stage_name="$(basename "$stage_dir")"
    if [[ -d "$stage_dir/.git" ]]; then
        die "stage dir is its own git repo (appears as submodule): $stage_name/.git"
    else
        info "No .git inside $stage_name"
    fi
done

# 2. No submodules
if [[ -f "$CLONE_DIR/.gitmodules" ]] && grep -q '\[submodule' "$CLONE_DIR/.gitmodules" 2>/dev/null; then
    die ".gitmodules present — remove all submodules"
else
    info "No git submodules."
fi

# 3. No symlinks anywhere in repo
SYMLINKS="$(find "$CLONE_DIR" -not -path "*/.git/*" -type l 2>/dev/null)"
if [[ -n "$SYMLINKS" ]]; then
    die "Symlinks found (not allowed):\n$SYMLINKS"
else
    info "No symlinks."
fi

# 4. Each stage-N/ has Dockerfile and RUN.md
for stage_dir in "$CLONE_DIR"/stage-*/; do
    [[ -d "$stage_dir" ]] || continue
    stage_name="$(basename "$stage_dir")"
    [[ -f "$stage_dir/Dockerfile" ]] || die "$stage_name/Dockerfile missing"
    [[ -f "$stage_dir/RUN.md" ]]     || die "$stage_name/RUN.md missing"
    info "$stage_name has Dockerfile and RUN.md."
done

# 5. room.json exists
if [[ -f "$CLONE_DIR/room.json" ]]; then
    info "room.json present."
else
    warn "room.json not found — must be added before final submission."
fi

# 6. No credential-looking strings (harness check covers this, but extra grep)
CRED_PATTERN='(AKIA[A-Z0-9]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{32,}|band_[a-zA-Z0-9_]{20,})'
if grep -rE "$CRED_PATTERN" "$CLONE_DIR" \
        --include="*.json" --include="*.yaml" --include="*.yml" \
        --include="*.md" --include="*.env" -l 2>/dev/null | grep -v "\.git/"; then
    die "Potential credentials found in the above files. Rotate and replace before pushing."
else
    info "No credential patterns found."
fi

# 7. Every mandate has Harness: and Model: lines
MANDATE_DIR="$CLONE_DIR/mandates"
if [[ -d "$MANDATE_DIR" ]]; then
    for md in "$MANDATE_DIR"/*.md; do
        [[ -f "$md" ]] || continue
        name="$(basename "$md")"
        grep -qiE "^[-*_ \t]*Harness[*_ \t]*:" "$md" || die "$name is missing 'Harness:' line"
        grep -qiE "^[-*_ \t]*Model[*_ \t]*:"   "$md" || die "$name is missing 'Model:' line"
        info "$name has Harness: and Model: lines."
    done
else
    die "mandates/ directory missing from clone."
fi

# ── harness run --all --mode isolated ────────────────────────────────────────

echo ""
echo "[preflight] Checking stage directories for harness run …"

HAS_STAGES=0
for stage_dir in "$CLONE_DIR"/stage-*/; do
    if [[ -d "$stage_dir" ]]; then
        HAS_STAGES=1
        break
    fi
done

if [[ $HAS_STAGES -eq 1 ]]; then
    echo "[preflight] Running harness run --all --mode isolated …"
    mkdir -p "$CHECKS_BASE"
    TS="$(date -u +%Y%m%d-%H%M%S)"
    OUT_DIR="$CHECKS_BASE/preflight-${TS}"

    if "$HARNESS_PYTHON" -m harness run \
            --track pocketful \
            --repo "$CLONE_DIR" \
            --all \
            --mode isolated \
            --out "$OUT_DIR"; then
        info "harness run completed. Report: $OUT_DIR/report.json"
    else
        die "harness run returned non-zero. Report: $OUT_DIR/report.json"
    fi
else
    warn "No stage-* folders found in repository. Skipping harness run (run this again after your band implements stage-1)."
fi

# ── summary ──────────────────────────────────────────────────────────────────

echo ""
if [[ $FAILED -eq 0 ]]; then
    echo "✅  preflight PASSED — repository looks ready to submit."
else
    echo "❌  preflight FAILED — fix the issues above before submitting."
    exit 1
fi
