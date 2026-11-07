# Security policy and current boundaries

Report vulnerabilities privately to `thewhitefalcon13@proton.me`. Do not publish
unpatched vulnerabilities or secrets in public issues.

FactoryOps has three distinct execution modes:

- Native Switch/Codex: four supervised seats with automatic approvals disabled.
  Separate working directories and `isolation: isolated` are not demonstrated
  OS sandboxes. Agents inherit owner permissions. Prompts are procedural policy.
- Legacy Band/OpenCode: host execution requires explicit unsafe opt-in. Removing
  one environment variable does not prevent same-UID credential access. Never
  use it for adversarial workloads or treat it as the native Switch demo.
- Trusted verification runner: exports bounded regular Git blobs for an exact
  clean SHA; excludes runtime `.switch`, `.git`, `.codex` and `.env` data.
  Container commands request nonroot, read-only mounts/root, no network,
  no capabilities, no privilege escalation and CPU/memory/PID/time/output bounds.
  Production clearance requires real effective-containment tests, not flags or
  mocked engine responses alone.

In supervised mode, the report is a human-reviewed demonstration with procedural
approval, not an authoritative release. Enforced mode requires the controller.
The private SQLite controller ledger binds candidate manifest, independently
executed receipts, authenticated native verifier acknowledgments, request nonce,
opaque owner/room/message IDs and event order. Generic prose/regexes and caller
PASS booleans do not authorize completion. Only the controller's signed local
artifact is authoritative. Agents can still post ordinary conversation; that is
not a release decision. Failed checks, changed candidates, rejection and stream
loss revoke pending authorization. Replay cursors and generation fences survive
normal restart; gaps/takeover stop for operator recovery.

Controller keys/state must reside outside all agent-writable directories under a
separate OS principal. Mode0700 and HMAC do not isolate malicious same-UID host
processes. Native provider tool permissions, credential exclusion and deployment
separation must be verified before production use. Local fixture preparation
uses cooperative locks/atomic writes and refuses aliases; it does not defend
against an unrestricted same-UID process racing shared Git administration.

Never print/copy `.env`, agent configuration or auth files. Discord credentials
belong in Switch's connection form; observer credentials belong only in private
controller configuration. Native credentials must never be mounted into test
containers. HTTP/WebSocket bearer calls stay on configured loopback origins,
with redirects/proxies disabled. Source/log/message text is untrusted data.

Historical independent local review is not final clearance for later changes.
Live integration, fresh independent Inspector/Stresser clearance, effective
native permissions and operational recovery remain separate release gates.
See [the setup/verification runbook](docs/hackathon-2026/DEMO_RUNBOOK.md) for actual
operator checks; no production clearance is implied by local test success.
