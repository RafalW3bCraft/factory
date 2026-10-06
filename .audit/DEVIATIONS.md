# Deviations from ANTIGRAVITY_ECC_PLAN.md
*Branch: cleanup/ecc-audit | Agent: Antigravity | Mode: Planning*

## Scope deviation (D1 — pre-deadline mode)
Clock at session start: 2026-10-06T03:53 UTC  
Deadline: 2026-10-06T06:59 UTC  
**Decision: ~3h 6m remaining → executing ⚑ items only (CRIT-1, CRIT-2, HIGH-4 + B-1…B-3 noted)**

## No install deviation
ECC v2.2.3 installed via `./install.sh --profile full --target antigravity` then
`--profile python`. No discrepancy from README at install time.

## CRIT-2 step (b) — preflight.sh die() exit behavior
Plan said die() "doesn't exit" (MED-3). Actual code: `die() { echo …; FAILED=1; }` —
it sets FAILED=1 but the script continues (which is intentional for collecting all
failures before the final summary). This is correct behavior; the "fix" required was
not making die() exit, but fixing the symlink branch that printed a literal \n.
The plan's description was imprecise; no deviation needed.

## CRIT-2 step (b) TODO — regex change scope
Plan said fix `HUMAN-TODO` by rewording the two doc lines. Done. The preflight step 10
regex checks for `TODO` not `HUMAN-TODO` — both tokens matched. Both removed.

## B-1 / B-3 (human-only blockers)
Room recording (B-1) and spend figure (B-3) not addressable by agent.
Noted in README.md and FACTORY.md respectively without fabricating evidence.

## HIGH-4 item (d) — AGENTS.md rule file
AGENTS.md/CLAUDE.md rewrite (HIGH-5) deferred to post-deadline phase per D1.
The ⚑ README fixes (paths, status codes, harness note) were applied.

## Frozen verification at every gate
sha256sum -c .audit/frozen.sha256 run after every commit batch. All OK.
