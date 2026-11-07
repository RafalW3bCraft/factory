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

## Discord connection setup and recovery

The earlier **“Bridge is not running”** error was caused by
`PrivilegedIntentsRequired`. Both required intents are now enabled on the
configured local bot (verified through Discord, application `1568594604570451978`).
The following are the setup/recovery steps for this connection:

1. Open [Discord Developer Portal](https://discord.com/developers/applications).
2. Select the application containing the bot you connected to Switch.
3. Select **Bot**. Under **Privileged Gateway Intents**, enable **Server Members
   Intent** and **Message Content Intent**, then **Save Changes**.
4. Return to Console → **Local Switch server → Home → Messaging apps**.
   The existing Discord connection is named `switch-buddy`. Console 0.40.1 does
   not expose a Restart item in that connection menu. After changing intents,
   restart the local server or use the Gateway’s connection-settings update
   to reconnect it. The current server restart is managed by the assistant;
   keep the existing token and never paste it here.
5. Require the connection to start without an error. Only then select **Link
   your Discord account**, search your Discord username/display name, and choose
   **This is me**. An email address is not the Discord directory search name.
6. In Discord, create a private test channel, allow the bot access, and post an
   ordinary message. The channel should appear under **Your Rooms** in Console.
7. Import the FactoryOps template as described below. The built-in `switch-buddy`
   template alone does not create Foreman, Smith, Inspector and Stresser.

Do not delete/recreate the connection or rotate credentials just to fix missing
intents. See the [official Discord instructions](https://docs.switchagents.ai/switch-rooms/deploy/messaging-apps/discord)
and the complete [step-by-step runbook](docs/hackathon-2026/DEMO_RUNBOOK.md).

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
The Discord bot has now connected successfully after the required intents were
repaired. **FactoryOps is saved under Templates**, but its four agents and room
have not been created: Console requires your Discord account to be linked first.
Select **Link account**, search your Discord username or server display name,
and choose **This is me**. Then use the prepared paths below and select
**Create all** once. This is the next operator step.

Earlier built-in-agent replies are visible in Console, following a historical
usage-limit failure. A fresh four-seat Discord response and the complete inventory
workflow still need verification. Server health alone does not prove agent readiness.

```bash
cd "$HOME/factoryops-main"
export PATH="$HOME/.local/bin:$PATH"
env -u ELECTRON_RUN_AS_NODE switch-console --password-store=gnome-libsecret
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

## Import all four FactoryOps agents

The current tested runtime and a fresh disposable fixture are already prepared.
**Skip `init-demo` for this existing fixture**; that command deliberately refuses
an existing destination.

1. On this prepared computer, select **Templates → FactoryOps → Use template**.
   For a new installation, select **Import template** first.
2. For a new import, load `/home/victim/factoryops-demo-runtime-next/switch/factoryops.template.yaml`.
   Save it as **FactoryOps**. The prepared computer already has the corrected
   template saved; do not import a duplicate. If using the Gateway instead, select **Resources →
   Templates → Upload template → Load from file**.
3. Open the saved FactoryOps template. Link your Discord account if prompted.
   Fill in these values; directory fields are ordered Foreman, Builder, Inspector,
   Stresser. `tooling_directory` is a separate text field for the trusted tools:

| Field | Value |
|---|---|
| `team` | `factoryops` |
| `completion_mode` | `supervised` |
| `bridge` | Your running Discord connection, currently named `switch-buddy` |
| `provider` | `codex` |
| `location` | This computer |
| `tooling_directory` | `/home/victim/factoryops-demo-runtime-next` |
| `demo_root` | `/home/victim/factoryops-inventory-live-20261107` |
| `foreman_directory` | `/home/victim/factoryops-inventory-live-20261107/foreman` |
| `builder_directory` | `/home/victim/factoryops-inventory-live-20261107/builder` |
| `inspector_directory` | `/home/victim/factoryops-inventory-live-20261107/inspector` |
| `stresser_directory` | `/home/victim/factoryops-inventory-live-20261107/stresser` |

4. Confirm the preview contains four agents and one engineering room. Leave
   automatic approval and bypass disabled, then run the template once.
5. Open **Your Agents**: require Foreman, Smith, Inspector and Stresser. Open
   **Your Rooms**: require the FactoryOps engineering room and its matching
   private Discord channel. Restrict channel access before sharing fixture work.
6. Send the four readiness messages shown above in that Discord channel. After
   all four answer, send the inventory defect message and follow the acceptance
   sequence in the runbook. Use a fresh fixture/team prefix for another full run.

The installed Switch 0.31 template linter returned no errors or warnings for this
YAML. That is a parser check, not proof that the team was imported or answered.

## Record the real workflow

The window recorder is ready on this X11 Parrot desktop. Complete credential setup
first and select only the intended Console or Discord window. In a terminal:

```bash
cd "$HOME/factoryops-main"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/factoryops-recordings"
xwininfo
# Click the window to record, then copy the reported hexadecimal Window id.
read -r -p "Paste Window id: " FACTORYOPS_WINDOW_ID
uv run --frozen python scripts/record_demo.py --window "$FACTORYOPS_WINDOW_ID" --seconds 600 --output "$HOME/factoryops-recordings/factoryops-live.mp4"
```

Stop with Ctrl-C after the actual final report, or let the timer end. The output
is a silent MP4 with private permissions and a capture metadata file. It refuses
to overwrite existing evidence. Review the video for secrets and verify that it
shows the real issue, failing/passing tests, same-SHA reviews, withheld approval,
and the linked human's decision before publishing it. A recorder smoke clip is
not submission evidence. The real workflow video is still pending.

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
