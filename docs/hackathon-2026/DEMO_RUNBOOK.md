# FactoryOps live demonstration and verification

This is the canonical setup guide. Switch Console 0.40.1 is installed on the current Parrot computer. Server,
provider, and Discord readiness must each be verified; installation alone does
not establish them. Credentials and linked-human decisions require the operator. Local tests and simulated transports are not live evidence.
Do not use `start-factory.sh`: it starts the separate legacy Band/OpenCode mode.

## 1. Development environment

Use the user-owned `main` checkout. Its base is
`197601dcd264044397943c3c7932ceed704a75c2`, which includes the audited
`0bf8841ee584669b2786429f7ea677fdd4210de2` event implementation:

```bash
cd "$HOME/factoryops-main"
export PATH="$HOME/.local/bin:$PATH"
codex --version
codex login status
uv --version
uv sync --frozen --all-groups --python 3.12
uv run --frozen factoryops --help
uv run --frozen factoryops doctor
```

Do not capture raw login output in evidence: record only version, exit code and
sign-in method, without account identifiers. The existing extension supplies
Codex; do not install another copy or copy authentication files. The approved
executable is exposed at `~/.local/bin/codex`. `uv==0.12.10` is installed in the
isolated `~/.local/share/factoryops/tools` virtual environment.

Do not source `.env` for native Switch. Legacy provider variables are unrelated
to the chosen Codex ChatGPT sign-in. Missing sign-in requires the operator's
native sign-in, not a substitute key/provider.

## 2. Start Switch Console; install only if absent

Check `dpkg-query --show switch-console`. Do not reinstall the current verified
package merely to start it. On a new Linux amd64 machine, download `switch-console-amd64.deb` from the
[0.40.1 official release](https://github.com/sandbox-quantum/switch/releases/tag/switch-console-v0.40.1).
Its published size is **267006312 bytes** and SHA-256 is:

```text
7a7cd1cc2c3a33f748252db14ebf399c8359046ed434942bcfbd641ca78ccd8e
```

The verified local installer is in the cache path below. On a new machine use
the actual downloaded path. Check the complete file before installation:

```bash
sha256sum "$HOME/.cache/factoryops/installers/switch-console-amd64.deb"
sudo apt install "$HOME/.cache/factoryops/installers/switch-console-amd64.deb"
```

The operator performs `sudo`. Never install a partial/mismatched download.
Launch with `~/.local/bin` available, using the installed desktop command:

```bash
env -u ELECTRON_RUN_AS_NODE PATH="$HOME/.local/bin:$PATH" switch-console --password-store=gnome-libsecret
```

The IDE may set `ELECTRON_RUN_AS_NODE`; remove it only for this launch as shown.
Console has been opened successfully on the current computer. Its temporary
loopback control API is not the Switch collaboration server and must not be used
as `--switch-url`. Keep the desktop session open. In Console create/start a local server and
record its actual Server address. Console 0.40.1 bundles server 0.31.0.
[Console 0.40 supports a local server without Docker](https://docs.switchagents.ai/switch-rooms/resources/changelog).
Do not remove `podman-docker` for this native Discord setup.

In Console's provider setup, select Codex, refresh discovery, and require both
CLI installed and signed in. Launch Console with `~/.local/bin` on its PATH if
provider discovery fails. An IDE sign-in is not proof of Switch compatibility.
Follow the [official provider setup](https://docs.switchagents.ai/switch-rooms/getting-started/set-up-agent-providers).
Probe the actual local address, for example replacing the port below:

```bash
uv run --frozen factoryops doctor --strict --switch-url http://127.0.0.1:ACTUAL_PORT
```

Replace `ACTUAL_PORT` with the address Console displays. `doctor --strict`
returns nonzero if a required local executable, Codex login, or explicitly checked
Switch public health prerequisite fails. HTTP 200 on `/health` establishes server
reachability only. `doctor --require-live` deliberately fails closed: local
diagnostics cannot establish native seat or Discord readiness.

## 3. Connect Discord

### Current failure and recovery

The native server log contains `discord.errors.PrivilegedIntentsRequired`, followed
by `Discord gateway connection failed`. This explains **Bridge is not running**
when account linking searches the member directory. It is a Discord bot intent
configuration failure; local `/health` can still return HTTP200.

Open Discord Developer Portal → the connected bot application → Bot → Privileged
Gateway Intents. Enable Server Members Intent and Message Content Intent, then
Save Changes. Console0.40.1’s connection menu has no Restart item. Reconnect by restarting
the managed local server or updating the existing connection settings in the
Gateway; require a healthy connection before trying directory search.
Search your Discord username/display name and select This is me; do not search
by email or enter tokens in chat. Bot-owner portal access and the real account
selection remain operator steps. Voice-related PyNaCl/davey warnings are not the
cause of this text-chat connection failure.


Follow the [official Discord procedure](https://docs.switchagents.ai/switch-rooms/deploy/messaging-apps/discord):

1. Create a Discord application and bot in the Developer Portal.
2. Enable Server Members and Message Content privileged intents; save.
3. Invite it using `bot` and `applications.commands` scopes. Use the official
   permission list: View Channels, Send Messages, Send Messages in Threads,
   Manage Webhooks, Manage Channels, Manage Roles, Read Message History,
   Attach Files and Add Reactions.
4. Console → Messaging Apps → Connect → Discord: enter the bot token and server
   ID directly in that form. Never put the token in chat, Git, command history
   or captured output.
5. Link the real human identity using **This is me**. Restrict the bot and test
   agents to a dedicated private test channel using Discord permissions.
6. Test one addressed harmless greeting. Require a genuine Codex reply in the
   correct Switch room before importing the full team. A normal channel message
   may be needed to create the room; slash commands alone are not enough.

If authentication, download, certificates or discovery fail, retain a sanitized
error and stop the dependent step. Do not disable TLS verification or substitute
credentials. Record the actual UI/provider outcome.

## 4. Prepare the supervised four-agent demo

After automated checks and independent review, copy the tested candidate into
`~/factoryops-demo-runtime-next` without credentials, state, logs or caches. Keep it
unchanged during recording. Its base SHA plus a SHA-256 content manifest identify
uncommitted Factory changes. Development continues in `~/factoryops-main`.
Do not describe an unreviewed copy as a cleared runtime.

From that frozen runtime create a **new** disposable fixture outside every
Factory checkout; the path below must not already contain data:

```bash
cd "$HOME/factoryops-demo-runtime-next"
uv sync --frozen --all-groups --python 3.12
uv run --frozen factoryops init-demo --root "$HOME/factoryops-inventory-live-20261107" --completion-mode supervised
```

The existing prepared fixture must not be overwritten. If it already exists,
reuse its validated emitted paths or choose a genuinely new disposable root.
For a new enforced workflow use `--completion-mode enforced`; do not mix modes.
Save emitted paths, completion mode, and baseline SHA. Import `switch/factoryops.template.yaml`
in Console, select native Codex and the private Discord bridge. Set:

| Template field | Local value |
|---|---|
| `tooling_directory` | `/home/victim/factoryops-demo-runtime-next` |
| `demo_root` | `/home/victim/factoryops-inventory-live-20261107` |
| `completion_mode` | `supervised`, matching fixture metadata and instructions |
| `foreman_directory` | emitted `foreman` directory |
| `builder_directory` | emitted `builder` directory |
| `inspector_directory` | emitted `inspector` directory |
| `stresser_directory` | emitted `stresser` directory |

Use the actual field names shown by template import. Match `completion_mode`
to fixture metadata; changing only a prompt does not migrate the workflow mode. Keep all automatic
approval/bypass settings disabled. Require four native seats. Foreman's
`owner-agents` addressing admits sibling handoffs; human approval still belongs
only to the genuine linked operator. Role worktrees/prompts are supervised
organization, not OS isolation. Never give agents the Factory source checkout
or controller state directory as their working directory.

## 5. Record the actual manual acceptance

Before the issue, run `!agents-status` in the connected channel. Then address
each of `@factoryops-foreman`, `@factoryops-smith`, `@factoryops-inspector`, and
`@factoryops-stresser` with a different unpredictable harmless challenge, for
example `Reply exactly READY-<fresh random value>; do not change any files.`
Require the correct native seat to answer in the correct room within 120 seconds.
A connected bot, public health result, or another seat replying is insufficient.
If a seat fails, stop the workflow and follow the
[official troubleshooting steps](https://docs.switchagents.ai/switch-rooms/using/agent-not-answering).

For each action retain genuine output and exit code. Run only disposable local
inventory fixtures. Do not run endless autonomous missions.

| Step | Action | Required observation |
|---|---|---|
| 1 | Send `@factoryops-foreman Restock accepts -1 and lowers inventory. Please investigate and fix it.` | Defect ID and self-contained Smith handoff. |
| 2 | Watch Smith add and run a regression test. | Real RED failure for non-positive restock. |
| 3 | Watch Smith implement the fix and run the full fixture suite. | GREEN and full local fixture commit SHA. |
| 4 | Prepare each verifier using commands below. | Both detached at the exact SHA and clean. |
| 5 | Inspector inspects source and runs its own tests. | Actual SAST/review verdict and commands. |
| 6 | Stresser probes zero, negative and positive quantities. | Rejections leave inventory unchanged; commands pass. |
| 7 | Withhold approval. | Foreman asks after both passes and waits. |
| 8 | Linked human approves the identified candidate. | Actual identity, SHA, request/reply order and text. |
| 9 | Observe final report. | Label `human-reviewed demonstration`, correct candidate, actual checks and honest limitations; no authoritative release claim. |
| 10 | After idle time, send a fresh addressed status request. | New genuine reply, proving continuing availability. |

```bash
uv run --frozen factoryops prepare-verifier --root "$HOME/factoryops-inventory-live-20261107" --role inspector --commit FULL_SHA
uv run --frozen factoryops prepare-verifier --root "$HOME/factoryops-inventory-live-20261107" --role stresser --commit FULL_SHA
```

In each verifier directory independently run:

```bash
git rev-parse HEAD
git status --porcelain --untracked-files=all
python -B -m unittest discover -s tests
```

The supervised demo uses **operator-checked procedural approval**. Its final
report must be labeled **human-reviewed demonstration** and must not claim an
automatically authorized release. Native agent
conversation cannot be prevented from making premature claims by a Python
helper. Preserve the genuine transcript; never call a regex or claimed identity
authenticated authorization. Do not push/merge/deploy the fixture repository.
Only its disposable local commits are authorized.

Separate negative scenarios require fresh fixtures: verifier rejection, human
rejection/ambiguity, candidate change, stopped seat, timeout and path/symlink
escape. Expect withheld completion and unchanged external files. Duplicate
stream/restart scenarios belong to the additional controller below.

## 6. Optional production controller verification (separate from the demo)

Use an enforced-mode fixture/template for this path. The non-AI observer is a
**fifth infrastructure participant**, while the four AI
seats stay native. It must have its own registration and agent key. Never reuse
a Console-managed native session key/connection. A takeover is a final stop.
Use the [official registration and agent protocol](https://docs.switchagents.ai/switch-rooms/internals/agent-protocol)
and [connection contract](https://docs.switchagents.ai/switch-rooms/internals/agent-connection).

Store private JSON configuration outside repositories/fixtures, mode 0600. It
contains `server_url` (actual loopback HTTP/HTTPS base), `agent_id`, `api_key`,
`observer_participant_id`, `room_id`, `owner_id`, and `seats` with `inspector`
and `stresser`, plus `demo_root` naming the managed disposable fixture. Obtain opaque participant IDs from authenticated Switch room
participants; do not infer IDs from names or prefixes. `agent_id` and the
observer's participant ID are distinct configuration values.

Also configure `required_seats` with all four roles (`foreman`, `smith`,
`inspector`, `stresser`) mapped to their opaque authenticated participant IDs,
and `seat_addresses` mapping those roles to their actual native addresses. All
seat IDs must be distinct from one another, the owner, and the observer. The
Inspector/Stresser IDs must match the existing verifier `seats` mapping. These
fields are mandatory; older configuration/state needs a fresh configured
workflow, with prior evidence preserved rather than silently reused.

Register once with a Gateway **registration** key; the helper
`factory.switch_gate.register_observer` implements documented POST `/agents`
and refuses overwrite. The returned agent key is for the observer only. Invite
that observer to the private room. Do not print or export keys into agents or
execution containers. Registration, mapping and actual handshake are operator
steps until real Switch is running.

Build the dedicated test image, record its immutable local ID, then run actual
isolated checks (replace all uppercase placeholders):

```bash
docker build -f Dockerfile.verifier -t factoryops-verifier .
docker image inspect --format '{{.Id}}' factoryops-verifier
uv run --frozen factoryops verify --state /PRIVATE/controller-state --config /PRIVATE/controller.json --root /DEMO_ROOT --role inspector --commit FULL_SHA --image sha256:IMAGE_ID
uv run --frozen factoryops verify --state /PRIVATE/controller-state --config /PRIVATE/controller.json --root /DEMO_ROOT --role stresser --commit FULL_SHA --image sha256:IMAGE_ID
uv run --frozen factoryops gate --state /PRIVATE/controller-state --config /PRIVATE/controller.json
```

At startup and when a candidate is selected, the gate sends bounded challenges
containing `FACTORYOPS_READY ROLE NONCE`. All four configured native seats must
reply with the exact role/nonce from the correct authenticated identity and room
within 120 seconds. Caller flags, display names, and cached PASS claims cannot
replace these observations. Failure withholds approval/report. Recheck after
idle time; public server health never supplies seat readiness.

Each actual native reviewer must review the receipt and send exactly
`VERIFIED ROLE FULL_SHA RECEIPT_SIGNATURE` from its configured identity, or
`REJECT ROLE FULL_SHA RECEIPT_SIGNATURE`. Only after both receipts and native
acknowledgments does the observer request the exact candidate-specific human
confirmation. Generic `yes`, negative replies and wrong senders cannot approve.
The controller binds its own request to its observed platform message ID.

`factoryops status --state ... --config ...` is informational. Add `--strict`
to require a fresh observer stream; add `--require-live` to additionally require
current trusted readiness from all four configured native seats. These failures
return nonzero and cannot be overridden by a caller-supplied PASS claim.
`factoryops report --state ... --config ...` reads a signed local completion
artifact only if authorization was issued and remains current. Ordinary room
prose is never that artifact. Failed reruns, changed candidates, stream loss and
rejections revoke authorization. Logs/receipts/cursors stay in the private state
directory. A blocked gap/takeover requires operator reconciliation; preserve
old evidence and create a fresh workflow rather than silently skipping history.

A functioning supported engine is required for actual contained execution, not
for the native Discord setup. Rootless Podman through the existing Docker
wrapper has executed local containment probes; that does not prove Docker Engine
or native provider containment. If choosing Docker Engine, its setup is separate:
the reviewed Parrot package route replaces
`podman-docker` while retaining Podman. The operator first reviews
`apt-get --simulate install docker.io docker-compose`, installs with sudo, and
verifies Engine, Compose and user access. Do not assume wrapper availability is
a working Docker daemon. Effective native-provider permissions and a separate
controller OS principal are still required: unrestricted same-UID agents can
read controller/provider files despite wrappers or prompt rules.

## 7. Automated gate, recording and session lifecycle

```bash
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy src tests
uv run --frozen shellcheck *.sh scripts/*.sh
TMPDIR="$HOME/factoryops-local-tests" uv run --frozen pytest -q --cov=src --cov-fail-under=85
uv run --frozen pip-audit
uv build
uv run --frozen python scripts/sync_assets.py --check
uv run --frozen python scripts/check_supply_chain.py
git diff --check
```

Create `$HOME/factoryops-local-tests` first if absent. Also run pinned Bandit source scanning, installed-wheel resource smoke and
lock/export/SBOM parity. Report scan severity and actual exit codes, including
failures. Container configuration tests and mocked engine results are not
executed containment proof. Historical CI does not verify this uncommitted copy.

Keep Console's actual local server and managed agent controller running in the
current login session. Record process ownership, server address, health result,
runtime fingerprint, fixture SHA and evidence locations. Only claim "running"
after healthy dependencies AND a fresh genuine addressed Discord response.
Stop a native session using its controls under **Your Agents**; stop a foreground
optional gate with Ctrl-C. Console 0.40.1's Discord connection menu does not have
a Restart item. The current owned core service was gracefully restarted using
its existing executable/environment while retaining PostgreSQL; that is an
assistant-managed diagnostic action, not a documented Console button. User-facing
local-server restart and reboot persistence remain unverified. Keep the same
server/room and frozen directories for subsequent agent sessions. Never use broad `pkill` or the legacy stop
script for native Switch. Reboot persistence has not been promised or tested.

Capture redacted real room evidence in `LIVE_DEMO_EVIDENCE.md`, plus a short
video demonstrating the real workflow, reproduction instructions and public
repo/video links. Publish only with separately authorized Factory commits and
pushes. The operator submits on the official event page. The deadline is
**November 7, 2026 at 13:29 EST** ([official event](https://www.wemakedevs.org/hackathons/switch)).
Prepared materials are not a submission receipt. Never replace pending records
with fabricated messages, approvals or test results.

## Current connection status and next step

On November 7 the local server at `http://localhost:40735` answered `/health`
with HTTP 200. After the bot intent repair, its current startup log confirms a
successful Discord Gateway connection with no privileged-intent rejection.
FactoryOps version 2 is saved under **Templates**. The creation form is waiting
for the operator's **Link account → This is me** selection. Use a Discord username
or server display name, not an email. Creating four agents/one room and obtaining
their genuine replies remain pending. The tooling path is an independent text
field; the four Directory fields are agent workspaces only.

An earlier provider quota error is historical. Existing built-in-agent replies
are visible, but a new challenge and the four-seat acceptance run are separate
checks. Restore capacity in the same account if that error recurs. Launch Console with:

```bash
env -u ELECTRON_RUN_AS_NODE PATH="$HOME/.local/bin:$PATH" switch-console --password-store=gnome-libsecret
```

Use the desktop's secret-store unlock dialog if prompted. Never disable credential
protection or put keyring passwords in commands. Leave Console open during the test.

## Recording on this desktop

The repository's `scripts/record_demo.py` captures one explicitly selected X11
window into a private, silent MP4; it does not verify the workflow. The current
user-owned FFmpeg7.1.5 installation was extracted from checksum-verified Parrot
packages without system installation. Add `~/.local/bin` to PATH. An optional
imageio-ffmpeg download was cancelled after the OS-packaged recorder worked.

Use `xwininfo`, click the intended Console or Discord window and copy its Window
id. Close credential forms and notifications before capture. From the main
checkout run, replacing the window id with the freshly reported value:

```bash
mkdir -p "$HOME/factoryops-recordings"
read -r -p "Paste Window id: " FACTORYOPS_WINDOW_ID
uv run --frozen python scripts/record_demo.py --window "$FACTORYOPS_WINDOW_ID" --seconds 600 --output "$HOME/factoryops-recordings/factoryops-live.mp4"
```

Stop with Ctrl-C after completion or allow the timer to end. Existing files are
never overwritten; choose another name for another attempt. Review the whole
recording, trim only for presentation while retaining the original, and verify
all claimed milestones against genuine messages/commands. Capture metadata
always starts with `workflow_verified: false`; human review and actual workflow
evidence determine submission suitability. The three-second setup-only capture
in private evidence is not a hackathon demonstration.

### Verified intent repair

Discord's authenticated application endpoint identified the configured bot as
`switch- buddy`, application `1568594604570451978`, and initially reported flags0.
After the operator authorized both intents, the documented
`PATCH /applications/@me` updated only the two limited intent flags. Discord
returned HTTP200 and flags557056, confirming Server Members and Message Content
enabled. Existing credentials were retained in the service; no token was output
or added to repository files. The owned local core service was restarted using
its existing configuration. The subsequent current-startup log confirms a successful bot Gateway connection.
The real user link and four-seat workflow remain pending; they are not implied
by the HTTP flag update.
