# FactoryOps readiness record — November 7, 2026

## Current candidate and evidence scope

Active source is `/home/victim/factoryops-main`, branch `main`, based on
`197601dcd264044397943c3c7932ceed704a75c2`. This includes the audited event base
`0bf8841ee584669b2786429f7ea677fdd4210de2`. Factory changes remain uncommitted and
unpushed; a base SHA alone does not identify their contents. Preserve the shared
checkout's intentional deletions, its private configuration, the frozen runtime
during recording, and `hardening/prod-ready`.

This record separates **executed local evidence**, **historical CI**, and
**live Switch/Discord evidence**. The current implementation/docs revision is
under verification. Earlier successful checks below are historical local results,
not a claim that the latest edits have passed. External sanitized evidence lives
at `/home/victim/factoryops-evidence`.

**Submission verdict: pending real workflow, reviewed recording, publication,
and submission. Production verdict: not cleared.**

## Hackathon requirements

| Requirement | Current state | Evidence needed for PASS |
|---|---|---|
| A person and an AI agent perform a real task through Switch in team chat | UNVERIFIED | Genuine addressed issue, native inference/handoff, work and human response in the connected room |
| Switch is central to the business workflow | PARTIAL | Four-seat native template/source and corrected README exist locally; actual executed workflow still needed |
| Practical Track 01 workflow | PARTIAL | Disposable inventory defect scenario exists; live RED/GREEN and reviewed result needed |
| Reproducible technical execution | PARTIAL | Historical local gate passed; latest candidate must pass and reproduce using the guide |
| README and video/public deliverables | PARTIAL | Local guide prepared; real short video and reviewed public repository/video links pending |
| Eligibility, event-period work, team registration and timely submission | UNVERIFIED | Operator confirms eligibility/provenance/team and retains actual submission receipt |

Existing agents/libraries/templates are allowed; the Switch setup and workflow
must be built during the event. Teams may have up to four people. The published
deadline is **November 7, 2026,1:29 PM EST**. Check the
[official event requirements](https://www.wemakedevs.org/hackathons/switch)
before submission. Prepared materials are not a submission receipt.

## Historical executed local results

These results apply to the earlier reviewed implementation fingerprint
`552058f39cf271c2d67bab305f6825d75cf4217c7386e1506ec97260c48598b2`, not automatically
to subsequent edits:

- Project Python 3.12.14 and `uv==0.12.10`; frozen dependency installation completed.
- Existing IDE Codex CLI `0.162.0-alpha.2`: local ChatGPT sign-in and a direct
  genuine CLI response succeeded. Neither establishes Switch provider readiness.
- Full native local suite: **183 passed, 13 subtests, 88.10% coverage**, exit0.
- Ruff lint/format, mypy, shellcheck, package build, installed-wheel resources,
  and lock/export/SBOM parity passed; 78 public dependency versions matched.
- Native pip-audit exited0, no known vulnerabilities; the local Factory package
  was skipped because it is not on PyPI. Separate public locked dependencies
  also passed without that skip.
- Bandit 1.9.4 exited1: **17 low, 0 medium, 0 high** findings. These are review alerts,
  not a zero-finding scan pass.
- Local disposable TDD: RED 1, GREEN 0; both contained verifier executions exited0
  at the same fixture SHA, cleanup confirmed, completion withheld. This was local
  automation, not Smith's live work.
- Real rootless Podman probes exercised nonroot/read-only operation, denied
  disposable host access/loopback, absent credential environment/socket, dropped
  capabilities, no privilege escalation, limits, timeout, output cap and cleanup.
  These do not establish native Codex permissions.
- Independent development Inspector and Stresser reviewed the earlier local
  fingerprint, reproducing 76 and 78 tests respectively plus 4 subtests each. Their
  documented review-harness accommodations are not unmodified full-suite passes.

Logs include `final-checks.json`, `local-execution.json`, `containment.txt`,
`provider-smoke.json`, and `reviews/round2/`. No new remote CI result is implied.

## Current setup and feature matrix

Switch Console 0.40.1 is installed and has been opened successfully. Launching
from the IDE requires removing `ELECTRON_RUN_AS_NODE` for the Console process;
see the runbook. Its temporary loopback control API is not the Switch server.
The verified installer digest is
`7a7cd1cc2c3a33f748252db14ebf399c8359046ed434942bcfbd641ca78ccd8e`.
A running local server, Console Codex sign-in, Discord bridge and fresh native
responses must each be established separately. Follow
[DEMO_RUNBOOK.md](DEMO_RUNBOOK.md); do not infer those states from installation.

The private local `.env` has permissions 0600 and validated nonsecret legacy
settings. Native Switch/Codex credentials belong in their native configuration,
not `.env`. The previous full sandbox image build failed on a dependency-download
timeout; do not claim it is deployed from configuration alone.

| Feature | State / acceptance still needed |
|---|---|
| Four native seats, sibling addressing, supervised instructions | Implemented locally; import and actual handoffs unverified |
| Explicit supervised/enforced modes | Latest implementation under test; fixture/template/instructions must agree |
| Canonical paths, link checks, atomic metadata/rollback | Implemented/local regression evidence |
| Exact-SHA bounded snapshots and container receipts | Implemented; historical actual Podman execution |
| Candidate/attempt-bound ledger and signed report | Implemented/synthetic protocol tests; authenticated live observer pending |
| Informational and strict diagnostics/status | Latest implementation under test; public health never establishes all seats |
| Native required-seat freshness/failure handling | Latest implementation under test; mandatory four-role opaque IDs/address configuration and live authenticated challenge/timeout required |
| Separate controller OS principal and native effective permissions | Deployment/containment proof pending |
| Safe bootstrap, legacy lifecycle ownership and cleanup | Implemented/local tests; host mode remains unsafe opt-in |
| Package resources, reproducible ECC setup and supply parity | Implemented; rerun required after canonical resource edits |
| Deployment image, monitoring, restart/recovery, backup/restore | Incomplete/unverified in the actual production arrangement |

## Remaining work and acceptance

| Priority | Finding / relevant source | Acceptance |
|---|---|---|
| P0 submission | No genuine recorded Switch/Discord task (`switch/factoryops.template.yaml`, live evidence record) | Four addressed seat replies, real RED/GREEN, same-SHA independent checks, linked-human decision and fresh post-idle response |
| P0 submission | Mode/approval claims must match actual path (`src/factory/factoryops.py`, template, runbook) | Supervised report explicitly human-reviewed; enforced report unavailable without trusted current evidence; regression and actual transcript agree |
| P0 submission | Video, public tested candidate and submission receipt absent | Operator records/reviews video, separately authorizes publication, submits and retains receipt |
| P0 production | Controller/native workload boundary not proved (`workflow.py`, `switch_gate.py`, `verification.py`) | Separate principals; native tools denied private controller/provider data; real containment tests pass |
| P1 | Required-seat liveness and failure/recovery (`switch_gate.py`, `workflow.py`) | Authenticated all-seat freshness, stopped-seat timeout, reconnect/replay/takeover tests; unavailable seats block |
| P1 | Runnable deployment and supply reproducibility (`Dockerfile.sandbox`, package/assets/scripts) | Successful image build and offline smoke from current fingerprint; installed-wheel/resources and parity checks pass |
| P1 | Operational resilience (`workflow.py`, `switch_gate.py`) | Concurrent updates, restart, backup/restore, redacted logs, retained failure evidence and explicit recovery demonstrated |
| P2 | Maintainability and scaling | Profile realistic workload, document capacity/recovery objectives and improve modularity without weakening controls |

A readiness percentage is not a certification. Until the current candidate and
live criteria have evidence, no new percentage or release clearance is assigned.

## Documentation ownership and coverage

All 105 Markdown files were inventoried and read by the automated link/staleness
scan: 43 canonical ECC toolkit files, 4 legacy mandates, 47 packaged resource copies,
and 11 operator/history documents. Active operator docs were refreshed; useful
upstream development skills and historical provenance were retained. Three real
ECC link errors were corrected. ADR sample links remain illustrative examples.
Packaged copies are synchronized from canonical sources, not edited separately.

| Role | Owner |
|---|---|
| Contributor boundaries | `AGENTS.md` |
| Navigation/product overview | `README.md` |
| Setup/manual tests/troubleshooting/lifecycle | `DEMO_RUNBOOK.md` |
| Code map/trust boundaries | `ARCHITECTURE_AUDIT.md`, `SECURITY.md` |
| Current results/blockers | This file |
| Actual messages and approval/recording status | `LIVE_DEMO_EVIDENCE.md` |
| History/provenance | `CHANGELOG.md`, `docs/AUDIT.md`, `TDD_EVIDENCE.md` |

## Next verification

Run the exact automated gate from the demo runbook, plus pinned source scanning,
installed-wheel smoke, real containment and fresh independent reviews. Record
actual argv, exits, base SHA and content fingerprint. A failure blocks its
claims and dependent steps; add a meaningful regression before the smallest fix.
Missing credentials, authenticated approval, recording and submission are
operator tasks, never fabricated substitutes.
