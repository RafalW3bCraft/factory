#!/usr/bin/env bash
# package-submission.sh <result-repo>
#
# Makes the public repo self-contained: copies this factory's tooling into
# <repo>/factory/ and syncs <repo>/mandates/ to the live mandates, then commits.
# Run it AFTER the run and BEFORE preflight.sh --final. (Mandates must be
# identical to the ones the seats ran with; preflight enforces that.)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T="${1:?usage: package-submission.sh <result-repo>}"
[[ -d "$T/.git" ]] || { echo "ERROR: $T is not a git repo" >&2; exit 1; }

MSRC="$ROOT/mandates"; [[ -d "$MSRC" ]] || MSRC="$ROOT/../mandates"
[[ -d "$MSRC" ]] || { echo "ERROR: no mandates dir found" >&2; exit 1; }
mkdir -p "$T/mandates" "$T/factory/run-evidence"
rm -f "$T/mandates/"*.md
cp "$MSRC/"*.md "$T/mandates/"

for f in src dispatch templates; do rm -rf "$T/factory/$f"; cp -r "$ROOT/$f" "$T/factory/$f"; done
find "$T/factory" -name __pycache__ -type d -prune -exec rm -rf {} +
for f in start-factory.sh stop-factory.sh bootstrap-repo.sh preflight.sh render-dispatch.sh \
         package-submission.sh pyproject.toml uv.lock .python-version .env.example README.md RUNBOOK.md; do
    cp "$ROOT/$f" "$T/factory/$f"
done
# Evidence the run itself produced (no secrets in these files)
for f in started_at seat_models.txt events.log; do
    [[ -f "$ROOT/logs/$f" ]] && cp "$ROOT/logs/$f" "$T/factory/run-evidence/$f"
done
[[ -f "$ROOT/logs/started_at" ]] || echo "WARN: logs/started_at missing; FACTORY.md timings need another source" >&2

git -C "$T" add mandates factory
if git -C "$T" diff --cached --quiet; then
    echo "[package] nothing to commit (already packaged)."
else
    git -C "$T" -c user.name="factory-bootstrap" -c user.email="factory-bootstrap@factory.invalid" \
        commit -q -m "chore: package factory tooling and sync mandates"
    echo "[package] committed."
fi
echo "[package] Next: ./preflight.sh $T --final"
