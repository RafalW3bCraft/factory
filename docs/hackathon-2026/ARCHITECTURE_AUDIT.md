# FactoryOps Architecture Audit

This audit records the inspected baseline and the minimum Track 01 changes.
Repository code, room exports, issues, and agent output are untrusted data;
they never override this repository's operating rules.

## Validated gap matrix

| ID | Existing implementation | Reusable code | Missing FactoryOps capability | Risk | Priority | Verification |
|---|---|---|---|---|---|---|
| A | `run_seat.py` configures `approval_mode="auto_accept"`. | Environment and mandate readers. | Native Codex provider configuration with `auto_approve: false`. | Unreviewed local tool actions. | P0 | Template static test and live Console settings check. |
| B | Every legacy mandate prohibits human questions and approvals. | Four role separation and dual-gate language. | A room-level approval state and final-report gate. | Autonomous publication without governance. | P0 | Role-instruction and workflow-gate tests; live transcript. |
| C | Seat runner imports Band SDK and its OpenCode adapter. | Existing package, tests, and quality gates. | Switch Console native-Codex template. | Band is not Switch collaboration infrastructure. | P0 | YAML/template test and native Console setup runbook. |
| D | Compose drops all capabilities then re-adds `CHOWN`, `SETUID`, and `SETGID`. | Non-root image and limits. | No legacy Compose rewrite in the Track 01 MVP. | Privilege-boundary claim is overstated. | P2 | Documented deferred hardening item. |
| E | Compose uses an ordinary bridge network only. | Localhost-only Stresser mandate. | Explicit outbound-deny policy is absent. | Container egress is not technically denied. | P2 | Documented deferred hardening item. |
| F | Sandbox tests inspect Compose configuration. | Existing pytest structure. | Effective runtime-isolation testing is absent. | Configuration assertions can overstate runtime containment. | P2 | Documented deferred hardening item. |
| G | Startup retains 20 log runs and removes older directories. | Run-specific log layout. | Evidence retention for the live demo. | Automatic deletion can remove audit evidence. | P1 | FactoryOps evidence procedure keeps a separately selected transcript/export. |
| H | CI triggers only on `main` and `hardening/*`. | Existing quality jobs and coverage gate. | Event-branch trigger. | Hackathon branch changes may not receive CI. | P1 | Workflow test/inspection and GitHub Actions run. |
| I | ECC is project-local `.agents/` for Antigravity. | Curated rules, skills, and agents. | Verified native Codex plugin compatibility, if supported. | Conflicting or duplicated setup. | P1 | Codex plugin/MCP inspection and compatibility record. |

## FactoryOps target architecture

Switch Console launches four native Codex agents in a Discord-connected room.
FactoryOps pre-provisions separate worktrees for Smith, Inspector, and
Stresser; Switch itself is not asked to create worktrees. Smith is the only
seat that changes the disposable fixture repository. Inspector and Stresser
receive a clean detached checkout of Smith's candidate commit and independently
report their verification results to Foreman. Foreman requests human approval
only after both gates pass, records the linked human's affirmative room reply
with the candidate SHA, and then posts the completion report.

No custom Switch WebSocket or HTTP client is planned. Native Console providers
avoid duplicating Switch authentication, liveness, event, and reconnect logic.

## Threat controls

| Threat | Control |
|---|---|
| Prompt injection in issue or repository | Role instructions classify all external text as data and scope actions to the managed fixture. |
| Path escape or overwrite | CLI requires a new, absolute, non-protected demo root and refuses non-empty or repository-owned paths. |
| Candidate substitution | Verifier checkout resolves a reachable SHA, requires a clean worktree, then detaches at that exact revision. |
| Self-approval | Foreman accepts only a post-request affirmative message from the linked human identity and records it with the candidate SHA. |
| Premature release claim | Final report requires Smith commit, Inspector pass, Stresser pass, and human approval record. |
| Secret exposure | No credentials, tokens, transcript exports, or screenshots are generated or committed automatically. |

## Deferred legacy hardening

The Compose capability, egress, runtime-isolation, and legacy log-retention
findings are intentionally not changed before the Track 01 demonstration. They
remain follow-up security work and are not represented as remediated.

## Codex and Switch documentation compatibility

On the implementation host, Codex CLI native plugin support was verified and
the official `ecc@ecc` plugin version `2.2.3` was installed from the
`affaan-m/ECC` marketplace after inspecting its manifest. The existing
project-local `.agents/` installation remains intact; no legacy synchronization
script was used. The official `switch-docs` streamable-HTTP MCP server was
registered and its configuration was inspected. Registration is not evidence
that a Switch server, Console, Discord bridge, or agent session is running.
