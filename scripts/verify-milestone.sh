#!/usr/bin/env bash
# verify-milestone.sh — Deterministic verifier for Dark Factory milestones (Finding H8).
#
# Verifies that:
#   1. The target git repository and specified revision exist.
#   2. The working tree has no uncommitted changes (git status is clean).
#   3. The specified verification/test command executes with exit code 0.
#
# Usage:
#   ./scripts/verify-milestone.sh <repo-path> [commit-hash] [test-command...]
set -euo pipefail

if [[ $# -lt 1 || "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: ./scripts/verify-milestone.sh <repo-path> [commit-hash] [test-command...]"
    exit 0
fi

REPO="$1"
REVISION="${2:-HEAD}"
shift 2 2>/dev/null || shift $#
TEST_CMD=("${@:-}")

echo "=== Dark Factory Milestone Verifier ==="
echo "Target repo: $REPO"
echo "Revision:    $REVISION"

# 1. Verify directory and git repo
if [[ ! -d "$REPO/.git" ]]; then
    echo "ERROR: $REPO is not a git repository." >&2
    exit 1
fi

# 2. Verify commit exists
COMMIT_HASH="$(git -C "$REPO" rev-parse --verify "$REVISION" 2>/dev/null || echo '')"
if [[ -z "$COMMIT_HASH" ]]; then
    echo "ERROR: Revision '$REVISION' not found in repository." >&2
    exit 1
fi
echo "Verified commit hash: $COMMIT_HASH"

# 3. Verify clean git status
STATUS="$(git -C "$REPO" status --porcelain)"
if [[ -n "$STATUS" ]]; then
    echo "ERROR: Working tree is dirty (uncommitted changes found):" >&2
    echo "$STATUS" >&2
    exit 1
fi
echo "Verified working tree: clean"

# 4. Run test verification command if provided
if [[ ${#TEST_CMD[@]} -gt 0 ]]; then
    echo "Executing verification command: ${TEST_CMD[*]}"
    if ! (cd "$REPO" && "${TEST_CMD[@]}"); then
        echo "ERROR: Verification command failed with non-zero exit code." >&2
        exit 1
    fi
    echo "Verified test execution: exit code 0"
fi

echo "RESULT: Milestone verification PASSED."
exit 0
