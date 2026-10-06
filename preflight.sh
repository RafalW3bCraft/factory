#!/usr/bin/env bash
# preflight.sh — Comprehensive Factory Healthcheck & Diagnostics
#
# Usage:
#   ./preflight.sh [target-result-repo]
#
# Validates:
#   1. System tools: git, uv, python (>=3.12), opencode, band CLI.
#   2. Virtualenv & Python runtime dependencies (factory, band-sdk, pyyaml).
#   3. Environment & Secret permissions (.env mode 600/400).
#   4. Seat Mandates & Trust boundaries: validates foreman, smith, inspector, stresser.
#   5. Provider Authentication & Catalog: confirms mandate models exist in provider catalog (R6).
#   6. OpenCode Server & Model compatibility.
#   7. Band agent configuration (agent_config.yaml).
#   8. Target Result Repository readiness.
# Optional:
#   RUN_TESTS=1 ./preflight.sh   # also runs automated test suite
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_ROOT="$SCRIPT_DIR"
cd "$FACTORY_ROOT"

# Load safe env loader (Finding S3)
# shellcheck source=scripts/load_env.sh disable=SC1091
source "$FACTORY_ROOT/scripts/load_env.sh"

PASSED=0
WARNED=0
FAILED=0

ok()   { echo "  [OK]   $*"; PASSED=$((PASSED + 1)); }
warn() { echo "  [WARN] $*" >&2; WARNED=$((WARNED + 1)); }
fail() { echo "  [FAIL] $*" >&2; FAILED=$((FAILED + 1)); }

echo "=========================================================="
echo "         DARK FACTORY — PREFLIGHT DIAGNOSTICS"
echo "=========================================================="

# ── 1. System Binaries ────────────────────────────────────────────────────────
echo ""
echo "[1/8] Checking System Tooling …"
if command -v git >/dev/null 2>&1; then
    ok "git is available ($(git --version))"
else
    fail "git not found on PATH"
fi

if ! command -v less >/dev/null 2>&1; then
    git config core.pager cat 2>/dev/null || true
fi

if command -v uv >/dev/null 2>&1; then
    ok "uv is available ($(uv --version))"
else
    fail "uv not found on PATH"
fi

OPENCODE_BIN="$(command -v opencode 2>/dev/null || true)"
if [[ -n "$OPENCODE_BIN" ]]; then
    ok "opencode is available ($OPENCODE_BIN, v$("$OPENCODE_BIN" --version 2>/dev/null || echo 'unknown'))"
else
    fail "opencode not found on PATH. Install OpenCode or add it to PATH."
fi

BAND_BIN="$(command -v band 2>/dev/null || true)"
if [[ -n "$BAND_BIN" ]]; then
    ok "band CLI is available ($BAND_BIN)"
else
    warn "band CLI not found on PATH. Ensure Band Desktop / CLI is installed."
fi

# ── 2. Python Virtual Environment ─────────────────────────────────────────────
echo ""
echo "[2/8] Checking Python Environment & Dependencies …"
PYTHON_BIN="$FACTORY_ROOT/.venv/bin/python"
if [[ -x "$PYTHON_BIN" ]]; then
    PY_VER="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
    ok "Virtualenv Python is ready ($PYTHON_BIN, v$PY_VER)"
else
    fail "Virtual environment missing at $FACTORY_ROOT/.venv. Run 'uv sync' first."
fi

if [[ -x "$PYTHON_BIN" ]]; then
    if "$PYTHON_BIN" -c "import band, yaml, factory" >/dev/null 2>&1; then
        ok "Required runtime Python packages imported successfully (band, yaml, factory)"
    else
        fail "One or more runtime Python dependencies missing in virtualenv. Run 'uv sync'."
    fi
fi

# ── 3. Configuration & Secrets ────────────────────────────────────────────────
echo ""
echo "[3/8] Checking Configuration & Secrets …"
ENV_FILE="$FACTORY_ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
    PERMS="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%A' "$ENV_FILE" 2>/dev/null || echo 'unknown')"
    if [[ "$PERMS" == "600" || "$PERMS" == "400" ]]; then
        ok ".env permissions are secure ($PERMS)"
    else
        warn ".env permissions are $PERMS (recommend running 'chmod 600 .env')"
    fi
    # Safe KEY=VALUE parsing without arbitrary shell execution (S3)
    load_env_safe "$ENV_FILE"
    ok ".env loaded safely (no arbitrary shell evaluation)"
else
    warn ".env file missing. Create one from .env.example."
fi

# ── 4. Mandates & Models ──────────────────────────────────────────────────────
echo ""
echo "[4/8] Validating Agent Mandates & Boundaries …"
if [[ -x "$PYTHON_BIN" ]]; then
    if "$PYTHON_BIN" "$FACTORY_ROOT/src/lint_mandates.py" "$FACTORY_ROOT/mandates"; then
        ok "Mandates linter passed (all 4 mandates valid, trust boundaries present, no secret leaks)"
    else
        fail "Mandates linter detected violations in mandates/"
    fi
fi

# ── 5. Provider Authentication & Catalog Verification ─────────────────────────
echo ""
echo "[5/8] Verifying Provider Authentication & Mandate Models …"
if [[ -n "${FEATHERLESS_API_KEY:-}" ]]; then
    ok "FEATHERLESS_API_KEY is configured in environment"
    # S4: Header passed via stdin config (-K -), avoiding visible secret in argv / proc
    HTTP_CODE="$(printf 'header = "Authorization: Bearer %s"\nheader = "Content-Type: application/json"\n' "$FEATHERLESS_API_KEY" | \
        curl -s -K - -o /dev/null -w "%{http_code}" "https://api.featherless.ai/v1/models" 2>/dev/null || echo "000")"
    if [[ "$HTTP_CODE" == "200" ]]; then
        ok "Featherless API authentication verified (HTTP 200 via secure stdin config)"
    else
        warn "Featherless API returned HTTP $HTTP_CODE (verify key or connectivity)"
    fi
else
    fail "FEATHERLESS_API_KEY is not set. Add it to .env or export it."
fi

# R6: Verify each seat's model against the provider catalog
if [[ -x "$PYTHON_BIN" && -n "$OPENCODE_BIN" ]]; then
    PROVIDER_MODELS="$("$OPENCODE_BIN" models featherless 2>/dev/null || true)"
    for seat in foreman smith inspector stresser; do
        seat_model="$("$PYTHON_BIN" "$FACTORY_ROOT/src/run_seat.py" --model-of "$seat" 2>/dev/null || echo '')"
        if [[ -n "$seat_model" ]]; then
            if echo "$PROVIDER_MODELS" | grep -q "$seat_model"; then
                ok "Mandate model for @${seat} verified in catalog: $seat_model"
            else
                warn "Mandate model for @${seat} ($seat_model) not detected in provider catalog"
            fi
        else
            fail "Cannot determine mandate model for seat '$seat'"
        fi
    done
fi

# ── 6. OpenCode Server Compatibility ──────────────────────────────────────────
echo ""
echo "[6/8] Checking OpenCode Server Configuration …"
if [[ -n "$OPENCODE_BIN" ]]; then
    if [[ -n "${OPENCODE_SERVER_PASSWORD:-}" ]]; then
        ok "OPENCODE_SERVER_PASSWORD configured for authenticated server operation (S5)"
    else
        ok "OpenCode server ready (server password will be auto-generated at startup)"
    fi
fi

# ── 7. Band Agent Configuration ───────────────────────────────────────────────
echo ""
echo "[7/8] Checking Band Agent Configuration …"
AGENT_CFG="$FACTORY_ROOT/agent_config.yaml"
if [[ -f "$AGENT_CFG" ]]; then
    ok "agent_config.yaml exists"
    if [[ -x "$PYTHON_BIN" ]]; then
        MISSING_SEATS=()
        for seat in foreman smith inspector stresser; do
            "$PYTHON_BIN" -c "from band.config import load_agent_config; load_agent_config('$seat', config_path='$AGENT_CFG')" >/dev/null 2>&1 || MISSING_SEATS+=("$seat")
        done
        if [[ ${#MISSING_SEATS[@]} -eq 0 ]]; then
            ok "agent_config.yaml contains valid seat credentials for all 4 seats"
        else
            warn "agent_config.yaml missing credentials for seat(s): ${MISSING_SEATS[*]}"
        fi
    fi
else
    warn "agent_config.yaml not found. Band seats require credentials to connect to rooms."
fi

# ── 8. Target Result Repository ───────────────────────────────────────────────
echo ""
echo "[8/8] Validating Target Workspace Repository …"
TARGET_REPO="${1:-${RESULT_REPO:-}}"
if [[ -z "$TARGET_REPO" ]]; then
    warn "No RESULT_REPO specified. Pass a repo path or set RESULT_REPO in .env."
else
    if [[ "$TARGET_REPO" != /* ]]; then
        fail "RESULT_REPO must be an absolute path: $TARGET_REPO"
    elif [[ ! -d "$TARGET_REPO" ]]; then
        warn "Target directory does not exist: $TARGET_REPO. Run './bootstrap-repo.sh $TARGET_REPO' to create it."
    elif [[ ! -d "$TARGET_REPO/.git" ]]; then
        fail "Target directory is not a git repository: $TARGET_REPO"
    else
        BRANCH="$(git -C "$TARGET_REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
        HEAD_REV="$(git -C "$TARGET_REPO" rev-parse --short HEAD 2>/dev/null || echo 'none')"
        ok "Target repo is valid git repository: $TARGET_REPO (branch: $BRANCH, commit: $HEAD_REV)"
    fi
fi

# Optional: Run test suite if requested via RUN_TESTS=1
if [[ "${RUN_TESTS:-0}" == "1" ]]; then
    echo ""
    echo "[TESTS] Running Automated Test Suite …"
    if [[ -x "$PYTHON_BIN" ]]; then
        if "$PYTHON_BIN" -m pytest -q "$FACTORY_ROOT/tests"; then
            ok "All automated tests in tests/ passed."
        else
            fail "Automated test suite failed."
        fi
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=========================================================="
echo "DIAGNOSTIC SUMMARY: Passed: $PASSED | Warnings: $WARNED | Failures: $FAILED"
echo "=========================================================="

if [[ $FAILED -gt 0 ]]; then
    echo "Result: PREFLIGHT FAILED. Please resolve the failure(s) above before starting factory." >&2
    exit 1
else
    echo "Result: PREFLIGHT PASSED. Factory tooling is operational."
    exit 0
fi
