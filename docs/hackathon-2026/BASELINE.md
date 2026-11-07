# FactoryOps readiness record — November 7, 2026

## Verdict and candidate identity

**Hackathon: approximately 60% ready; submission blocked by the genuine four-agent
workflow, linked-human decision, reviewed video and final submission.**
**Production: approximately 55% ready; release blocked by unverified native
permissions, trusted host deployment and live recovery.** These are judgement
estimates of completed work, not certifications or measured reliability.

The authorized checkout is `/home/victim/factoryops-main`, branch `main`, HEAD
`26311912e10c27b1170df33720349f277a685fc8`. The operator externally committed/pushed
that revision during this session; the assistant issued no Factory commit/push.
Current additional changes remain uncommitted/unpushed. Earlier base:
`197601dcd264044397943c3c7932ceed704a75c2`; event audit base:
`0bf8841ee584669b2786429f7ea677fdd4210de2`.

Current implementation fingerprint: `f4510181389d1bb214f76812fe904dc7aa201f8c6d9e50bd13912fc00b9a3d93`.
The private manifest lists each measured file under
`/home/victim/factoryops-evidence/current-implementation-manifest.json`.
It includes implementation, tests, resources and configuration; operator/history
Markdown is excluded. A commit SHA alone does not identify these working edits.
The new runtime candidate is `/home/victim/factoryops-demo-runtime-next`.
The original frozen runtime and shared checkout deletions remain preserved.

## Verified, inferred and unknown

**Verified local:** 224 tests and 13 subtests passed; coverage 88.61%. All ten
commands below exited 0. The full sandbox dependency/image build succeeded after
bounded download retries; actual container containment and two-UID probes ran.
These are local checks, not live native agent or human decisions.

**Verified setup:** Switch Console 0.40.1/core 0.31.0 running; actual local server
`http://localhost:40735/health` returned HTTP 200. The Discord intent repair
returned HTTP 200 and the subsequent native core log confirms Gateway connected,
with no privileged-intent rejection. Corrected FactoryOps template is saved in
Console; the form shows four agents and waits for account linking.

**Inference:** a linked operator, available Codex capacity and successful native
session startup should permit the supervised inventory demonstration. That
inference is not a passed acceptance test.

**Unknown/pending:** correct human Discord identity, private channel readiness,
four fresh native seat replies, actual handoffs/RED/GREEN/same-SHA checks/approval,
reviewed video, registration/eligibility details and submission receipt. Built-in
agent replies visible in Console do not prove the FactoryOps workflow. An earlier
usage-limit error is historical; a fresh four-seat inference check is required.

## Mandatory hackathon requirements

PASS means evidence exists; FAIL means currently incomplete; UNKNOWN means the
operator or actual event receipt must supply evidence.

| Requirement | Result | Evidence / remaining action |
|---|---|---|
| Real task by at least one AI agent and a human through Switch/team chat | FAIL | No completed FactoryOps native workflow captured yet |
| Switch central to the submitted workflow | FAIL | Native four-agent template is implemented/imported; actual run pending |
| Track 01 practical business workflow | PARTIAL | Inventory issue scenario implemented; demonstrated business result pending |
| Clear README/reproduction instructions | PASS locally | README and canonical runbook corrected from executed setup; final published revision pending |
| Demonstration video and repository/submission deliverables | FAIL | Recorder works; genuine workflow video/public links/submission receipt pending |
| Team size/eligibility/registration and work during event | UNKNOWN | Operator confirmation and provenance required; existing agents/libraries/templates are allowed, Switch workflow must be event work |
| Deadline | UNKNOWN | Submission receipt must precede November 7, 2026, 13:29 EST |

[Official event requirements](https://www.wemakedevs.org/hackathons/switch).
Track fit is a judging consideration; local test coverage is a project quality
gate, not a substitute for the event's human/AI workflow requirement.

## Current automated commands and exits

Executed in `/home/victim/factoryops-main` with Python 3.12.14 and uv 0.12.10.
Test TMPDIR: `/home/victim/factoryops-local-tests`.

| Actual command | Exit | Result |
|---|---:|---|
| `uv run --frozen ruff check .` | 0 | Passed |
| `uv run --frozen ruff format --check .` | 0 | Passed |
| `uv run --frozen mypy src tests` | 0 | Passed |
| `uv run --frozen shellcheck *.sh scripts/*.sh` | 0 | Actual expanded argv retained in JSON |
| `TMPDIR="$HOME/factoryops-local-tests" uv run --frozen pytest -q --cov=src --cov-fail-under=85` | 0 | 224 passed, 13 subtests; 88.61% |
| `uv run --frozen pip-audit` | 0 | No known dependency vulnerabilities; local Factory package skipped because not on PyPI |
| `uv build` | 0 | Wheel and source distribution built |
| `uv run --frozen python scripts/sync_assets.py --check` | 0 | Canonical/package copies agree |
| `uv run --frozen python scripts/check_supply_chain.py` | 0 | 78 lock/export/SBOM versions agree |
| `git diff --check` | 0 | Passed |

Exact argv, elapsed time and exit codes: `current-final-checks.json`; command
output: `current-final-*.log` in private evidence. Mypy also passed with the new
recorder/principal-probe scripts included (45 files). Bandit 1.9.4 last scan
exited 1: **16 LOW, 0 MEDIUM/HIGH** alerts; this is not a zero-finding pass.
The final distribution smoke/image parity and narrow native-fix review records
are separate checks; use their actual artifacts before claiming their outcome.
No fresh remote CI result is asserted for these uncommitted edits.

## Implementation and remaining proof

| Feature | State | Actual evidence / limit |
|---|---|---|
| Native Foreman/Smith/Inspector/Stresser, sibling addressing, bypass off | Implemented; live unverified | Saved template; native lint passes; four sessions not created |
| Supervised/enforced mode consistency | Implemented | Local mode/mismatch tests; supervised report has limited procedural authority |
| Canonical fixture paths, symlink checks, Git relationships, atomic metadata | Implemented | Real disposable Git regression tests; advisory same-UID protection |
| Native `.switch` runtime state | Implemented | Regression preserves ignored runtime files through candidate preparation |
| Independent tooling path in Console | Implemented | RED then GREEN regression; corrected template saved as version 2 |
| Exact-revision, credential-free bounded execution | Implemented locally | Real Podman execution/limits/cleanup; not native provider isolation |
| Durable candidate/attempt-bound ledger and signed report | Implemented; live unverified | Synthetic authenticated event/replay/restart/expiry tests |
| Required-seat freshness and strict diagnostics | Implemented; live unverified | Four opaque identities, challenge freshness, durable retry budget and idle-stream tests |
| Cross-principal read-only candidate access | Partial | Real container UIDs 1000/1001: readonly source succeeds, mutation/private sentinel access denied; host deployment pending |
| Source/image/package/ECC reproducibility | Implemented locally | Frozen builds, resources, non-overwrite tests and supply parity; image identity must match final wheel |
| Legacy Band/OpenCode lifecycle | Implemented legacy path | Owned-process/descendant tests; unsafe host execution remains explicit opt-in |
| Monitoring, backup/restore, real observer recovery, native permissions | Partial/unverified | Production acceptance still required |

Independent development Inspector and Stresser previously returned **LOCAL PASS**
for a bounded core review, each independently running 40 tests and 4 subtests
(exit 0). Their Git-fixture sandbox limits are stated in the reports. These
reviewers are not the native Switch Inspector/Stresser seats. Fresh narrow
reviews of the last native-workspace/template fixes are recorded separately.

## Ordered remaining work

| Priority | Exact files / finding | Acceptance test |
|---|---|---|
| P0 submission | `switch/factoryops.template.yaml`, `docs/hackathon-2026/LIVE_DEMO_EVIDENCE.md`: missing real run | Link genuine human; create four seats/room; four addressed replies within 120 s; real Foreman handoff, Smith RED/GREEN/full SHA; Inspector/Stresser execute independently at same SHA; approval withheld then actual human decides; fresh post-idle response |
| P0 submission | `README.md`, `DEMO_RUNBOOK.md`, live record: video/public delivery pending | Record actual workflow with `scripts/record_demo.py`; review secrets and claims; operator authorizes publication, supplies public links and submission receipt |
| P0 production | `src/factory/switch_gate.py`, `workflow.py`, `verification.py`, `SECURITY.md`: host trust boundary unproved | Trusted controller code/config/state/key under separate OS principal; native tools denied controller/provider secrets and external disposable sentinels; do not rely on prompt rules or permission bits |
| P1 | `switch_gate.py`, `workflow.py`: actual authenticated observer/seat recovery unverified | Real opaque identity/room mapping, stopped-seat failure, idle heartbeat, duplicate/reconnect, restart, changed candidate and takeover; no stale or duplicate authorization |
| P1 | `Dockerfile.sandbox`, `Dockerfile.verifier`, `scripts/verify_containment.py`: exact final deployment proof | Final wheel installed outside source; image package hashes match; immutable-ID containment/limits/cleanup pass; documented operator lifecycle |
| P1 | `workflow.py`, `switch_gate.py`, `DEMO_RUNBOOK.md`: operational recovery | Backup/restore actual state, retained evidence/redacted logs, failure visibility and supported stop/restart; do not promise reboot persistence |
| P2 | `verification.py`, `workflow.py`, operator docs: maintainability/capacity | Review remaining LOW scan alerts, profile representative workloads, state capacity/recovery goals and improve structure without weakening controls |

## Manual interventions

1. Supply the actual Discord username/display name; select **This is me** for the
   correct account. The existing bot credentials stay in Switch, not `.env`.
2. Restrict the dedicated test channel, create the template once, confirm normal
   tool approvals and available existing-account capacity.
3. The operator must personally decide the identified candidate after both
   independent native checks; no assistant-generated human approval.
4. Review the real recording, confirm event/team eligibility, separately authorize
   Factory publication, submit and retain the actual receipt.
5. Production requires separate trusted host ownership and authenticated observer
   setup, effective native containment and recovery evidence.

## Next implementation prompt

> Work only in `/home/victim/factoryops-main` on main; no commits/pushes or changes
> to preserved checkouts/runtime. Read AGENTS.md and ECC TDD/security/verification
> guidance. Start from HEAD26311912e10c27b1170df33720349f277a685fc8 plus the current
> fingerprinted working changes. First complete the real supervised Switch/Discord
> four-seat run after operator identity linking; capture actual same-SHA RED/GREEN,
> independent verdicts and later genuine human decision. Fix only reproduced
> blockers test-first; never manufacture messages, approvals or a demo video.
> Then deploy the trusted observer under a separate OS principal, prove native
> tools cannot read controller keys/state/code or provider secrets, exercise real
> recovery/stopped-seat/takeover negatives and final immutable-image containment.
> Run the full documented gate, installed-wheel smoke and independent local
> Inspector/Stresser reviews; update canonical status/runbook/README from actual
> results. Keep publication/submission and human approval pending for the operator.

## Documentation ownership

All 105 Markdown files were inventoried: 43 canonical ECC toolkit files, 4 legacy
mandates, 47 packaged copies and 11 operator/history documents. Active guidance
was corrected; history/upstream skills retained, three real ECC links fixed,
and generated copies synchronized. Examples remain explicitly illustrative.

- `AGENTS.md`: contributor boundaries.
- `README.md`: entry point; `DEMO_RUNBOOK.md`: single setup/manual-test guide.
- `ARCHITECTURE_AUDIT.md` and `SECURITY.md`: code map/trust boundaries.
- This file: current outcomes/blockers; `LIVE_DEMO_EVIDENCE.md`: actual room evidence.
- `CHANGELOG.md`, `docs/AUDIT.md`, `TDD_EVIDENCE.md`: provenance/history.
