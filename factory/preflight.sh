#!/usr/bin/env bash
# preflight.sh — validate a result repository before submission.
#
# Usage:
#   ./preflight.sh <repo-path-or-url> [--final]
#
#   --final  submission gate: missing stages / room.json / placeholders / non-public
#            remote become FAILURES instead of warnings.
#
# What it does:
#   1. Fresh-clones <repo-path> (if it is a local path) into a temp dir,
#      or uses a remote URL via git clone.
#   2. Runs "python -m harness check <clone> --track pocketful".
#   3. Runs "python -m harness run --track pocketful --repo <clone>
#             --all --mode isolated" with output under CHECKS_DIR.
#   4. Asserts structural rules (no .git inside stage dirs, no submodules,
#      no symlinks, Dockerfile + RUN.md per stage, room.json present,
#      no credential patterns, mandate header lines present).
#
# Requires: git, python (with harness installed), docker daemon accessible.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$SCRIPT_DIR/.env" ]] && { set -a; source "$SCRIPT_DIR/.env"; set +a; }
CHECKS_BASE="${CHECKS_DIR:-${HOME}/checks}"

# Locate the event harness. An explicit HARNESS_REPO always takes precedence.
if [[ -n "${HARNESS_REPO:-}" ]]; then
    [[ -d "$HARNESS_REPO" ]] && HARNESS_REPO="$(cd "$HARNESS_REPO" && pwd)"
else
    HARNESS_REPO=""
    for candidate in \
        "$SCRIPT_DIR/../dark-factory-wearedevs" \
        "$SCRIPT_DIR/../../dark-factory-wearedevs" \
        "$SCRIPT_DIR/../../../dark-factory-wearedevs" \
        "$HOME/dark-factory-wearedevs"; do
        if [[ -d "$candidate" ]]; then
            HARNESS_REPO="$(cd "$candidate" && pwd)"
            break
        fi
    done
fi

# ── helpers ──────────────────────────────────────────────────────────────────

die()  { echo "FAIL: $*" >&2; FAILED=1; }
info() { echo "  OK: $*"; }
warn() { echo "WARN: $*"; }

FAILED=0

# ── args ─────────────────────────────────────────────────────────────────────

FINAL=0; REPO_ARG=""
for a in "$@"; do
    case "$a" in
        --final) FINAL=1 ;;
        -h|--help) REPO_ARG=""; break ;;
        *) REPO_ARG="$a" ;;
    esac
done
if [[ -z "$REPO_ARG" ]]; then
    echo "Usage: preflight.sh <repo-path-or-url> [--final]"
    echo ""
    echo "Validates the result repository before submission."
    echo "Pass either a local absolute path or a https://github.com/... URL."
    echo "--final turns warnings about missing stages, room.json, placeholders and a"
    echo "non-public remote into failures."
    exit 0
fi
# strict(): failure in --final mode, warning otherwise
strict() { if [[ $FINAL -eq 1 ]]; then die "$*"; else warn "$*"; fi; }
TMPDIR_BASE="$(mktemp -d)"
CLONE_DIR="$TMPDIR_BASE/clone"

cleanup() { rm -rf "$TMPDIR_BASE"; }
trap cleanup EXIT

# ── clone ────────────────────────────────────────────────────────────────────

echo "[preflight] Cloning repository …"
if [[ "$REPO_ARG" == http* || "$REPO_ARG" == git@* ]]; then
    git clone --depth=1 "$REPO_ARG" "$CLONE_DIR"
    REMOTE_URL="$REPO_ARG"
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
    strict "room.json not found — must be added before final submission."
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

# 8. Mandates are generic (track-specific detail = disqualification)
if [[ -f "$SCRIPT_DIR/src/lint_mandates.py" && -d "$MANDATE_DIR" ]]; then
    if python3 "$SCRIPT_DIR/src/lint_mandates.py" "$MANDATE_DIR"; then
        info "mandate lint clean."
    else
        die "mandates name track-specific detail (see above)."
    fi
fi

# 9. Mandates in the repo are the ones the factory actually ran
LIVE_MANDATES="$SCRIPT_DIR/mandates"; [[ -d "$LIVE_MANDATES" ]] || LIVE_MANDATES="$SCRIPT_DIR/../mandates"
if [[ -d "$LIVE_MANDATES" && -d "$MANDATE_DIR" ]]; then
    if diff -rq "$LIVE_MANDATES" "$MANDATE_DIR" >/dev/null 2>&1; then
        info "repo mandates are identical to the factory's live mandates."
    else
        die "repo mandates differ from $LIVE_MANDATES (stale copy? re-run package-submission.sh)."
    fi
fi

# 10. No leftover placeholders in the human-facing docs
for doc in FACTORY.md README.md; do
    if [[ -f "$CLONE_DIR/$doc" ]]; then
        if grep -nE 'TBD|TODO|FIXME|<!--|<kickoff-repo>|<this-repo>|add team name' "$CLONE_DIR/$doc"; then
            strict "$doc still has placeholders (above)."
        else
            info "$doc has no placeholders."
        fi
    else
        strict "$doc missing."
    fi
done

# 11. Literal secret values (from .env / agent_config.yaml / opencode.json) must not appear
#     anywhere in the repo or its history. The room export is the likely leak path.
SECRETS="$TMPDIR_BASE/secrets.txt"; : > "$SECRETS"
for f in "$SCRIPT_DIR/.env" "$SCRIPT_DIR/agent_config.yaml" "$HOME/.config/opencode/opencode.json"; do
    [[ -f "$f" ]] || continue
    grep -iE '(key|token|secret|password)' "$f" 2>/dev/null \
      | sed -E "s/^[^:=]*[:=][[:space:]]*//; s/^[\"']//; s/[\"',]*[[:space:]]*\$//" \
      | awk 'length($0) >= 16 && $0 !~ /\{env:/' >> "$SECRETS" || true
done
sort -u -o "$SECRETS" "$SECRETS"
if [[ -s "$SECRETS" ]]; then
    HITS="$(grep -rIlF -f "$SECRETS" "$CLONE_DIR" --exclude-dir=.git 2>/dev/null || true)"
    if [[ -n "$HITS" ]]; then
        die "a real secret value appears in the working tree (values not shown). Files:"$'\n'"$HITS"
    elif [[ "$(git -C "$CLONE_DIR" log --all -p 2>/dev/null | grep -cF -f "$SECRETS" || true)" -gt 0 ]]; then
        # grep -c (not -q): -q exits early, git gets SIGPIPE and pipefail reports "not found".
        die "a real secret value appears in git history (values not shown). Rotate it and rewrite history."
    else
        info "no live secret values in tree or history ($(wc -l < "$SECRETS") checked)."
    fi
else
    warn "no secret values found in .env/agent_config.yaml to scan for (is this run from the factory dir?)."
fi

# 12. Final-mode structure: contiguous stages from 1, parsable room.json, public remote
STAGES_FOUND="$(cd "$CLONE_DIR" && ls -d stage-[0-9]* 2>/dev/null | sed 's/stage-//' | sort -n | tr '\n' ' ' || true)"
if [[ -n "$STAGES_FOUND" ]]; then
    exp=1; gap=0
    for n in $STAGES_FOUND; do [[ "$n" == "$exp" ]] || gap=1; exp=$((exp+1)); done
    [[ $gap -eq 0 ]] && info "stages present: $STAGES_FOUND" || die "stage folders are not contiguous from 1: $STAGES_FOUND"
else
    strict "stage-1/ is the minimum for eligibility."
fi
if [[ -f "$CLONE_DIR/room.json" ]]; then
    python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$CLONE_DIR/room.json" 2>/dev/null \
        && info "room.json parses as JSON ($(du -h "$CLONE_DIR/room.json" | cut -f1))." \
        || die "room.json is not valid JSON."
fi
if [[ -n "${REMOTE_URL:-}" ]]; then
    WEB="$(echo "$REMOTE_URL" | sed -E 's#^git@github.com:#https://github.com/#; s#\.git$##')"
    CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$WEB" 2>/dev/null || echo 000)"
    case "$CODE" in
        200) info "remote is publicly reachable without login: $WEB" ;;
        000) warn "could not reach $WEB to confirm the repo is public (offline?)." ;;
        404) strict "remote returned 404 without login — repo is private or misspelled: $WEB" ;;
        *)   warn "could not confirm the repo is public (HTTP $CODE): $WEB — open it in a private window." ;;
    esac
else
    strict "no origin remote configured (judges need a public GitHub repo)."
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
    strict "No stage-* folders found in repository. Skipping harness run (run this again after your band implements stage-1)."
fi

# ── summary ──────────────────────────────────────────────────────────────────

echo ""
if [[ $FAILED -eq 0 ]]; then
    echo "✅  preflight PASSED — repository looks ready to submit."
else
    echo "❌  preflight FAILED — fix the issues above before submitting."
    exit 1
fi
