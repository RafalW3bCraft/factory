# FactoryOps architecture and trust boundaries

This is the current code map. [BASELINE.md](BASELINE.md) owns results and remaining
work; [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) owns executable setup/manual tests.
Earlier Track 01 design assumptions are superseded by the implemented separation
below. Inspect actual source before relying on a documented control.

## Native workflow

Discord ↔ Switch local server and managed runtime ↔ four native Codex seats:
Foreman coordinates, Smith changes the disposable Builder repository, Inspector
and Stresser review clean detached candidate worktrees, and the linked human
reviews the candidate. Switch owns native provider sessions and transport.

The supervised mode records the genuine human-reviewed demonstration. Its
procedural checks cannot stop an agent from making an unsupported claim in chat.
The enforced mode adds a separate trusted non-AI observer and contained execution
runner. The authoritative result is a signed local controller artifact, not
Foreman's prose. Four AI seats remain native; the observer is a fifth
infrastructure participant with its own authentication.

## Code map

| Area | Responsibilities | Regression coverage |
|---|---|---|
| `src/factory/factoryops.py` | Fixture lifecycle, canonical paths, worktrees, atomic metadata, CLI | `tests/test_factoryops.py` and fixture-hardening tests |
| `src/factory/verification.py` | Exact raw Git snapshots, credential-free bounded container execution, durable receipts/cleanup | Runner and containment tests |
| `src/factory/workflow.py` | Transactional ledger, revision/attempt fences, receipt authentication, approval/revocation, signed report | Workflow tests |
| `src/factory/switch_gate.py` | Separate observer registration, authenticated stream, message/request binding, recovery and takeover stops | Switch-gate protocol tests |
| `src/factory/diagnostics.py` | Sanitized tool/login and optional public transport checks | Diagnostics/CLI tests |
| `switch/factoryops.template.yaml` | Four native seats, sibling addressing, completion-mode instructions, disabled bypass approvals | Template/role instruction tests |
| `scripts/verify-milestone.sh` | Exact checked-out revision, clean worktree, mandatory checks | Milestone script tests |
| `scripts/sync_assets.py`, `src/factory/config.py` | Packaged public resources and non-overwriting ECC setup | Resource/package tests |
| `start-factory.sh`, `src/factory/run_seat.py`, `mandates/`, `dispatch/` | Separate unsafe opt-in legacy Band/OpenCode execution | Legacy lifecycle/runner tests |

## Boundaries that require evidence

| Risk | Implemented defense | Limit / remaining proof |
|---|---|---|
| Redirected fixture metadata/path escape | Derived paths, ownership/link checks, Git relationships, lock, atomic write/rollback | Cooperative local protection is not isolation against malicious same-user processes. |
| Candidate substitution | Clean exact SHA, bounded raw blobs, disabled Git replacement refs, manifest/revision fences | Final live reviewers must inspect the same candidate. |
| Forged/replayed approval | Controller binds opaque participants, room, actual request message, nonce, revision, order and expiry | Real authenticated observer mapping/handshake and restart need live execution. |
| Forged PASS | Trusted signed execution receipt plus native reviewer acknowledgment | Ordinary agent conversation cannot authorize release. |
| Untrusted execution | Nonroot read-only snapshot/container, no network/credentials/socket, resource/time/output limits, confirmed cleanup | Actual engine tests and effective native provider restrictions are separate gates. |
| Controller tampering | Private durable state/HMAC, intended separate OS principal | Same-UID permissions are insufficient. Cross-principal deployment must be tested. |
| Required seat unavailable | Readiness challenges and workflow blocking are required | Public `/health` alone proves only server reachability; native health enforcement needs supported APIs/live proof. |

No duplicate ECC plugin is required. `.agents/` is the canonical curated toolkit;
`src/factory/assets/` contains synchronized package copies. Native role workspace
instructions are generated for this workflow and must not inherit legacy
never-ask-the-human mandates. Installed plugin/MCP configuration, if present,
proves neither a running server nor a connected Discord room.
