#!/usr/bin/env bash
# Verify an exact checkout before and after a mandatory explicit command.
set -euo pipefail
# Inspect the named checkout, never an inherited alternate Git administration path.
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_INDEX_FILE
export GIT_NO_REPLACE_OBJECTS=1 GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
die() { echo "ERROR: $*" >&2; exit 1; }
usage() { echo 'Usage: verify-milestone.sh --repo PATH --commit FULL_SHA -- COMMAND [ARG...]'; }
if [[ ${1:-} == -h || ${1:-} == --help ]]; then usage; exit 0; fi
if [[ ${1:-} == --repo ]]; then
    [[ $# -ge 5 && $3 == --commit ]] || { usage >&2; exit 1; }
    REPO="$2"; REVISION="$4"; shift 4
    [[ ${1:-} != -- ]] || shift
else
    [[ $# -ge 2 ]] || { usage >&2; exit 1; }
    REPO="$1"; REVISION="$2"; shift 2
fi
[[ $# -gt 0 ]] || die 'A verification command is mandatory; no checks were executed.'
[[ "$REVISION" =~ ^[0-9a-f]{40}$ ]] || die 'Revision must be a full lowercase commit SHA.'
[[ "$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$REPO" rev-parse --is-inside-work-tree 2>/dev/null || true)" == true ]] || die 'Target is not a git working tree.'
assert_candidate() {
    [[ "$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$REPO" rev-parse HEAD)" == "$REVISION" ]] || die 'Checkout HEAD does not match the requested candidate.'
    [[ -z "$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -C "$REPO" status --porcelain --untracked-files=all)" ]] || die 'Working tree is dirty.'
}
assert_candidate
echo "Verified exact candidate: $REVISION"
set +e
(cd "$REPO" && "$@")
command_exit=$?
set -e
echo "Verification command exit code: $command_exit"
[[ $command_exit == 0 ]] || die 'Verification command failed.'
assert_candidate
echo 'RESULT: Milestone verification PASSED.'
