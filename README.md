# FactoryOps — fix an inventory issue with four AI teammates

FactoryOps brings an inventory defect from a Discord conversation through a
reviewed fix using **Switch Console and four native Codex agents**. Foreman
coordinates, Smith builds, Inspector reviews, Stresser tests failure cases, and
the linked human decides whether to accept the identified candidate.

[![CI](https://github.com/RafalW3bCraft/factory/actions/workflows/ci.yml/badge.svg)](https://github.com/RafalW3bCraft/factory/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Start here:** [setup and manual verification](docs/hackathon-2026/DEMO_RUNBOOK.md).
Use that guide for installation, Discord connection, team import, the real issue,
approval, troubleshooting, and stop/restart. Native Switch does not need the
legacy Band/OpenCode services or a Featherless API key.

## What the project does

1. A person reports that negative restocking lowers inventory.
2. Foreman sends Smith a self-contained task.
3. Smith demonstrates the failure with a test, fixes it, and supplies a commit
   from a disposable local repository.
4. Inspector and Stresser independently inspect and execute checks on that exact
   revision.
5. Foreman asks the linked human to review that candidate and records the actual
   decision before producing a demonstration report.

The default **supervised** demonstration uses human-checked procedural approval.
It is not an automatically enforced release authorization. The separate
**enforced** workflow requires contained execution receipts, authenticated native
reviewer acknowledgments, candidate-bound human confirmation, and a signed
controller artifact. Ordinary agent messages are never that artifact.

## Current status

The local implementation includes validated disposable worktrees, exact-revision
verification, bounded credential-free container execution, a durable approval
ledger, packaged ECC resources, and regression tests. Live Switch/Discord work,
automated tests, historical CI, and production isolation are separate evidence
categories.

See [current results and blockers](docs/hackathon-2026/BASELINE.md) and
[actual live evidence](docs/hackathon-2026/LIVE_DEMO_EVIDENCE.md). Missing live
results remain pending. A green public CI badge does not verify uncommitted local
changes, Discord integration, human approval, or production readiness.

## Run it on the current Parrot desktop

The local Switch server answered `GET /health` with HTTP **200** at
`http://localhost:40735` on November 7, 2026. Its database and server are running.
The Console database currently lists **zero native agents and zero sessions**;
the FactoryOps team still needs importing. The operator reports Discord connected;
a genuine addressed Discord reply has not yet been independently verified.

```bash
cd "$HOME/factoryops-main"
export PATH="$HOME/.local/bin:$PATH"
env -u ELECTRON_RUN_AS_NODE switch-console
```

Keep Console open: its managed agent watcher is required to start native Codex
sessions. A reachable server alone does not keep the four agents answering.
In Console, select **Local Switch server**, confirm Codex is installed/signed in,
then open **Messaging apps** and check Discord has no error. Link your Discord
account with **This is me**. Never put Discord credentials in this repository.

Next follow [team import and real acceptance](docs/hackathon-2026/DEMO_RUNBOOK.md#4-prepare-the-supervised-four-agent-demo).
Use the disposable fixture paths emitted by `factoryops init-demo`; do not use
this source checkout as an agent workspace. Import `switch/factoryops.template.yaml`
with `completion_mode=supervised`, then send the private Discord channel:

```text
!agents-status
@factoryops-foreman Reply with FACTORYOPS_FOREMAN_READY.
@factoryops-smith Reply with FACTORYOPS_SMITH_READY.
@factoryops-inspector Reply with FACTORYOPS_INSPECTOR_READY.
@factoryops-stresser Reply with FACTORYOPS_STRESSER_READY.
```

Require actual replies from all four seats within 120 seconds. Then send:

```text
@factoryops-foreman Restock accepts -1 and lowers inventory. Please investigate and fix it.
```

Watch the failing test, focused fix, exact commit, two independent checks and
linked-human approval. The [runbook](docs/hackathon-2026/DEMO_RUNBOOK.md) explains
the expected evidence and failure cases. Nothing is submitted automatically.

## Development

Use Linux, Python 3.12, and `uv==0.12.10`. Preserve the lockfile:

```bash
uv sync --frozen --all-groups --python 3.12
uv run --frozen factoryops --help
uv run --frozen factoryops doctor
uv run --frozen pytest -q --cov=src --cov-fail-under=85
```

The current authorized workspace is `/home/victim/factoryops-main` on `main`.
Factory changes remain uncommitted and unpushed. Preserve the original shared
checkout's intentional deletions and the frozen runtime during recording.
Publish only after separately authorized commits and pushes.

ECC is the checked-in development toolkit under `.agents/`: 10 rules, 12 agent
profiles, and 20 skills from the pinned upstream snapshot. Use research,
test-first changes, security review, independent Inspector/Stresser verification,
and executed evidence. Do not install a duplicate plugin merely to satisfy ECC.
`factoryops-ecc` installs the packaged snapshot into a separate target and refuses
conflicting files. Rule frontmatter is validated locally; it does not imply that
Codex automatically loads every Antigravity rule.

## Where to find information

| Need | Canonical source |
|---|---|
| Setup, live manual tests, troubleshooting, stop/restart | [Demo runbook](docs/hackathon-2026/DEMO_RUNBOOK.md) |
| Current evidence, feature status, remaining work | [Readiness record](docs/hackathon-2026/BASELINE.md) |
| Actual room messages, approvals, recording status | [Live evidence](docs/hackathon-2026/LIVE_DEMO_EVIDENCE.md) |
| Code map and trust boundaries | [Architecture](docs/hackathon-2026/ARCHITECTURE_AUDIT.md) |
| Security limitations and disclosure | [Security](SECURITY.md) |
| Contributor boundaries | [AGENTS.md](AGENTS.md) |
| Historical fixes and test provenance | [Changelog](CHANGELOG.md), [audit ledger](docs/AUDIT.md), [TDD evidence](docs/hackathon-2026/TDD_EVIDENCE.md) |
| Legacy Band/OpenCode operation | [Legacy reference](RUNBOOK.md) |

Important source areas are `switch/` (native team template), `src/factory/`
(fixtures, runner, ledger and observer), `tests/`, `scripts/`, `.agents/`, and
`mandates/`/`dispatch/` (legacy instructions). `src/factory/assets/` contains
synchronized distribution copies; edit their canonical sources, then run
`uv run --frozen python scripts/sync_assets.py`.

## Safety and data handling

Use disposable inventory fixtures and localhost-only probes. Agent worktrees and
permission bits do not isolate malicious same-user processes. Native provider
permissions and a separate controller OS principal need effective tests before
production clearance. Legacy host execution is explicitly unsafe for untrusted
workloads. See [SECURITY.md](SECURITY.md).

Codex processes the messages and source supplied through its provider. Switch
and Discord transport collaboration messages. Provider authentication stays in
its native configuration; Discord tokens go only into Console's connection form.
Never commit credentials or unreviewed transcripts. Do not assume prompts prevent
sensitive content from reaching a configured provider.

## Hackathon handoff

Track 01 demonstrates a practical business workflow with Switch central to the
collaboration. Follow the [official event requirements](https://www.wemakedevs.org/hackathons/switch)
for eligibility, event-period work, deliverables, and submission. A real reviewed
workflow, short video, public code/video links, and operator submission remain
separate from preparing local materials.

Released under the [MIT License](LICENSE).
