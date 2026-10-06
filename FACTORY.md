# FACTORY.md

> This file is the authoritative description of the **Pocketful Dark Factory**.
> It must be enough for another team to stand the factory up from scratch, without
> any additional explanation from us.

---

## Overview

This factory is a four-seat software factory built on
[Band Desktop](https://band.ai) with [OpenCode](https://opencode.ai) seats
powered by Featherless AI open-weights models. Its intended operating loop is
dispatch, implementation, independent review, and adversarial testing. The
recorded submission run required four human messages: an initial dispatch, a
duplicate after a timeout, a continuation after a long stall, and a steering
note. It also had three OpenCode timeouts; see the evidence below.

The four-stage pipeline is:

```
Human dispatch
    → Foreman (plans, coordinates, reports)
        → Smith (implements, commits)
            → Inspector (independent review, checks + spec gaps)
                → Stresser (resilience probes: retries, concurrency, restarts)
                    → Foreman (final report)
```

Each role has a mandate file in `mandates/` that says what it owns, how it
hands off, and what makes it reject work. The mandates are generic — they
describe *how the factory works*, not what pocketful asks for. You can point
them at any software project.

---

## Seats

| Role key | Band display name | Harness | Model | Setup commands |
|---|---|---|---|---|
| `foreman` | Foreman | OpenCode | `zai-org/GLM-5.3-Flash` | See *Stand it up from scratch* |
| `smith` | Smith | OpenCode | `zai-org/GLM-5.3-Flash` | See *Stand it up from scratch* |
| `inspector` | Inspector | OpenCode | `MiniMaxAI/MiniMax-M2.5` | See *Stand it up from scratch* |
| `stresser` | Stresser | OpenCode | `zai-org/GLM-5.3-Flash` | See *Stand it up from scratch* |

---

## Stand it up from scratch

The source checkout contains the seat mandates and factory tools. The factory
is an operator-run workflow, not a web app. It needs Python 3.12, `uv`, Git,
`curl`, OpenCode, BAND Desktop, a Featherless API key, and the event's separate
kickoff repository. Docker is required for isolated harness runs.

### Step 1 — Set paths

Run these commands from the repository root. The source tools live in
`factory/factory/` here; after `package-submission.sh`, they live in
`<result-repo>/factory/`.

```sh
export REPO_ROOT="$(git rev-parse --show-toplevel)"
if [ -f "$REPO_ROOT/factory/factory/pyproject.toml" ]; then
  export FACTORY_DIR="$REPO_ROOT/factory/factory"
else
  export FACTORY_DIR="$REPO_ROOT/factory"
fi
export WORK_ROOT="${WORK_ROOT:-$(dirname "$REPO_ROOT")}"
export RESULT_REPO="${RESULT_REPO:-$WORK_ROOT/result-final}"
export HARNESS_REPO="${HARNESS_REPO:-$WORK_ROOT/dark-factory-wearedevs}"
export CHECKS_DIR="${CHECKS_DIR:-$WORK_ROOT/checks}"
```

Clone the event kickoff repository into `$HARNESS_REPO` if it is not already
there. It is not included in this project.

### Step 2 — Install factory tools

```sh
cd "$FACTORY_DIR"
uv sync
chmod +x ./*.sh
cp .env.example .env
chmod 600 .env
```

Edit `.env` on your machine with the Featherless key and absolute result path.
Keep it private. The preflight script reads `HARNESS_REPO` and `CHECKS_DIR`
from the environment; export them in the shell where you run it.

### Step 3 — Configure OpenCode and BAND

Configure OpenCode with the Featherless provider and the models named by the
`Model:` lines in `mandates/*.md`. Register the four BAND agents using the
display names **Foreman**, **Smith**, **Inspector**, and **Stresser**, then
create the local `agent_config.yaml` expected by the BAND SDK. That file is
intentionally excluded from this repository; never commit its credentials.

### Step 4 — Install the event harness

Follow the kickoff repository's own installation instructions from
`$HARNESS_REPO`. Confirm that `python -m harness --help` works and that Docker
is available before starting an isolated test. If browser-based harness checks
are used, install the browser dependencies required by that harness.

### Step 5 — Create a result repository and start the factory

```sh
cd "$FACTORY_DIR"
./bootstrap-repo.sh "$RESULT_REPO"
./start-factory.sh
```

`start-factory.sh` reads `RESULT_REPO` and `FEATHERLESS_API_KEY` from the
environment or local `.env`, checks the seat configuration, and refuses to
continue if a seat fails its startup gate.

### Step 6 — Dispatch and stop

In a new BAND Desktop room, send Foreman the rendered task:

```sh
./render-dispatch.sh pocketful --stages 1
```

Monitor the factory logs, then stop the run with `./stop-factory.sh`. Record
every human intervention and timeout in the final account; do not describe a
run as autonomous if it required follow-up messages.

### Step 7 — Package and verify

Download the full BAND room export to `$RESULT_REPO/room.json`, then run:

```sh
./package-submission.sh "$RESULT_REPO"
./preflight.sh "$RESULT_REPO" --final
python "$FACTORY_DIR/src/analyze_room.py" \
  "$RESULT_REPO/room.json" --repo "$RESULT_REPO"
```

`preflight.sh --final` fresh-clones the Git repository and runs the event
harness. It needs `HARNESS_REPO` (or an installed `harness` module) and Docker.
Resolve every reported warning or failure before submission.

---

## Design choices and why

**Four seats, four roles.**
We chose a planner/builder/reviewer/hardener split rather than a
planner/builder split, because the rubric rewards reviews that change the work.
A dedicated reviewer that independently re-reads the spec reliably finds gaps
the builder's own checks miss.

**OpenCode on Featherless (GLM-5.3-Flash).**
OpenCode seats do not require a Docker Sandbox and work on Linux without
additional setup, which keeps the factory simple and portable. GLM-5.3-Flash
is fast, available on Featherless under the provided key, and handles the
code-generation and review tasks well enough for iteration.

**`question_mode=auto_reject`.**
The guide warns that OpenCode defaults to `manual`, which stalls the seat
waiting for a human answer. Setting `auto_reject` keeps every run dark. The
adapter also sets `approval_mode=auto_accept` so tool calls never pause.

**Mandate text injected as `custom_section`.**
Rather than baking roles into a separate prompt file, we inject the mandate
text via `OpencodeAdapterConfig.custom_section`. This means the same
`run_seat.py` script serves all seats; only the mandate file changes.

**Model guard in `run_seat.py`.**
The script reads the `Model:` line from the mandate and refuses to start if
the argument differs. This prevents a stale mandate from silently running
the wrong model during the graded submission.

**Result repo separated from factory inputs.**
The seats commit to `RESULT_REPO` (a separate git repo), not to the factory
directory. The `opencode serve` process is started from `factory/` so it
reads `~/.config/opencode/opencode.json`, never any file in the result repo.
This keeps credentials out of the result repo's git history.

**Operator safeguards live outside the seats.**
Seats stay generic; everything specific to *this* hackathon or machine is a
script the operator runs, so the mandates remain portable:
- `src/lint_mandates.py` fails the start if a mandate names endpoint paths, field
  names, status codes, header names or track vocabulary.
- `start-factory.sh` resolves each seat's model from its own mandate, refuses to
  declare the band up unless all seats survive ~15 s, and restarts a crashed seat
  (bounded, logged to `factory/run-evidence/events.log`). It sends nothing to the room.
- `render-dispatch.sh` is the single source of truth for paths, so the dispatch
  cannot point at a different repo than the one the seats commit to.
- `preflight.sh --final` fresh-clones the repo and runs the harness in isolated
  mode, and fails on leftover placeholders, symlinks, missing stage files, an
  unparsable `room.json`, a non-public remote, and any real secret value
  (from `.env` / `agent_config.yaml`) in the tree or in git history.

**Requirement IDs tie review to the spec.**
Foreman numbers every testable requirement (REQ-n) and cites the IDs in every
handoff; Inspector's verdict lists each ID as verified / not verifiable / failed
with evidence. Acceptance is therefore a statement about the spec, not about
the builder's own checks.

---

## What we tried that failed

_(append-only log — add entries as they happen)_

- **2026-10-03:** Initial Featherless API key probe via `urllib.request` returned
  HTTP 403 Forbidden.
  Root cause: Cloudflare WAF on `api.featherless.ai` blocks Python's default User-Agent
  (`Python-urllib/3.x`). With standard client headers (curl or OpenCode's Fetch runtime),
  the endpoint returns HTTP 200 OK.
  Resolution: Configured OpenCode provider in `~/.config/opencode/opencode.json` with
  `apiKey: "{env:FEATHERLESS_API_KEY}"`; verified models are visible and reachable.

- **2026-10-05 (pre-run audit of the tooling):** five defects found before the
  graded run; each now has a fix in this repository.
  1. The dispatch hard-coded one result-repo path while the final run used another,
     so the seats would have built outside the repo that gets submitted →
     templated dispatch + `render-dispatch.sh`.
  2. `start-factory.sh` forced a single model onto all seats although its header
     promised per-seat models, which made a different-model reviewer impossible →
     models are read from each mandate.
  3. Each mandate contained an author-facing rule ("do not name X in this
     mandate") inside the agent's own prompt, which can be misread as "never write
     endpoint paths in a handoff" → removed, enforced by the linter instead.
  4. The submission repo contained mandates but none of the tooling this file tells
     a judge to run → `package-submission.sh`.
  5. The result repo's `.gitignore` excluded `dist/` and `build/`, which can make a
     service build locally and fail from a fresh clone → no longer ignored.

---

## Measured time and model spend per stage

| Stage | Wall-clock start | Wall-clock end | Duration | Model spend |
|---|---|---|---|---|
| 1 | 2026-10-05 09:15 UTC (dispatch) | 2026-10-05 10:00 UTC (final report) | ~44 min | unverified (Featherless dashboard) |
| 2 | In progress (not committed) | — | — | — |
| 3 | Not reached | — | — | — |
| 4 | Not reached | — | — | — |

### Run facts (from `analyze_room.py` and the room export)

| Fact | Value |
|---|---|
| Human messages in the submitted room | **4** — initial dispatch (09:15 UTC); identical re-dispatch after timeout (09:34 UTC); one-word "continue" after ~1h55m stall (12:11 UTC); steering note to seats (12:18 UTC). See `docs/FACT_SHEET.md` §3 for message ids. |
| Total room messages | **683** (parsed from `room.json`) |
| Seat restarts (`events.log`) | 1 (`2026-10-05T12:39:09Z FATAL opencode server died`) |
| OpenCode timeouts (Smith) | 3 (09:33, 10:16, 12:33 UTC — `error` type messages in room.json) |
| Stall | ~1 h 55 m (10:16 UTC timeout to 12:11 UTC "continue") |
| Defects found by Stresser that led to a fix | 1 (C1: 0-byte bodies 422 to 400, commit `5620886`) |
| Defects self-found by Smith during fix verification | 1 (C2: cold-start missing indexes, same commit `5620886`) |
| Inspector rejections that changed the code | **0** (Inspector accepted `ef1a437` before C1/C2 were discovered) |
| Highest stage accepted / harness result | Stage 1 accepted (147/147 pass isolated mode, rev `5620886`) |

### Bad work the band caught (from the room; at least two, with revisions)

1. **Incident 1 — 0-byte request bodies returned HTTP 422 instead of HTTP 400:**
   - **Defect:** `parse_json_object` treated an empty request body as an empty JSON dict `{}`. Endpoints with required fields therefore raised validation failures and returned `422 validation_failed` instead of `400 malformed_request` per API specification §5.
   - **Found by:** **Stresser** (room.json msg `76888d2f` at `09:51:47Z`): labelled as "1 unresolved concern (cosmetic, low severity)" after Inspector had already accepted `ef1a437`.
   - **Escalated by:** Foreman (msg `582bedd8` at `09:52:12Z`): reclassified as DEFECT C1 and routed to Smith as a follow-up fix.
   - **Fixing revision:** `5620886` (msg `d3b53a55` at `09:57:03Z`). Uniform guard checks for empty body before parsing JSON.
   - **Inspector action on `ef1a437`:** ACCEPTED at `09:44:52Z` and `09:49:34Z` — before C1 was discovered. Inspector did NOT reject `ef1a437`.
   - **Inspector action on `5620886`:** Delta-ACCEPTED at `09:59:41Z` and `10:02:19Z`.
   - **Turns / Resolution:** 1 rework cycle triggered by Stresser, not Inspector.

2. **Incident 2 — Container cold-start index failure before first `POST /_test/reset` (self-found by Smith):**
   - **Defect:** Initial service state was instantiated without building derived indexes (user ID, handle, email, payment requests). Any call to `POST /auth/signup` or `POST /auth/login` on a fresh container prior to calling `POST /_test/reset` failed with a generic HTTP 400 error.
   - **Found by:** **Smith** (self-found during C1 fix verification; room.json msg `d3b53a55` at `09:57:03Z`): "Bonus defect found & fixed while verifying C1."
   - **Fixing revision:** `5620886`. Store indexes are now explicitly initialized at startup.
   - **Inspector action:** Delta-verified the fix in `5620886` review (msgs `b054d56f`, `efd0a80a`). Inspector did not find this defect.

**How to measure:**
- **Start:** First human dispatch message in `room.json`: `2026-10-05T09:15:48Z` (msg id `9cd51be9`).
- **End:** Foreman's Stage 1 final report in `room.json`: `2026-10-05T10:00:00Z` (msg id `2c37bc65`).
- **Spend:** Featherless subscription page -> Usage, filtered to the run dates, summed across all four seats. HUMAN-TODO: actual spend figure not captured.

---

## How the factory catches and recovers from bad work

1. **Inspector runs checks independently.**
   Inspector does not trust Smith's reported output. It checks out the exact
   committed revision, runs every supplied check, then re-reads the spec and
   tests behaviours the checks do not exercise. A rejection sends evidence
   back to Smith; Smith fixes and re-commits; Inspector re-reviews on the new
   revision.

2. **Stresser probes resilience after acceptance.**
   Even after Inspector accepts, Stresser runs adversarial probes: concurrent
   writes, repeated requests, malformed input, and restart-with-state.
   Defects found at this stage go back to Smith via Foreman; the review loop
   restarts.

3. **Foreman's final report records open defects.**
   If a defect cannot be fixed in time, Foreman records it explicitly in the
   stage outcome rather than silently accepting imperfect work. The room log
   shows the attempt and the evidence.

4. **`preflight.sh` catches submission problems.**
   Before pushing, run `./preflight.sh "$RESULT_REPO"` to fresh-clone
   the repo, run `harness check`, run `harness run --all --mode isolated`,
   and check for structural issues (missing Dockerfiles, .git inside stage
   dirs, credential patterns). This is the only check that catches a file
   missing from git history.

---

## Limitations

- **GLM-5.3-Flash context window.** On long specs the model may truncate.
  Foreman's mandate instructs it to split handoffs into numbered parts.
- **Single model, single provider (unless the mandates say otherwise).** Seats
  that share a model share blind spots; a reviewer on a different model family is
  the stronger design. Check `factory/run-evidence/seat_models.txt` for what ran. A Featherless outage halts the factory. Mitigation: the
  `opencode.json` can list fallback models; mandate the `model_id` change
  if switching.
- **No Docker Sandbox.** OpenCode seats run on the host and hold broad
  permissions. A seat that runs a harmful command reaches the host filesystem.
  Mitigation: run on a throwaway machine or VM for the final submission run.
- **Browser tests require browser dependencies.** Install the dependencies
  required by the kickoff harness before running its browser checks.
- **`harness run --mode isolated` requires Docker daemon access.**
  If Docker permission is denied, add the user to the `docker` group and
  open a new shell (`newgrp docker`).
- **Secrets can leak into the public room export.** Seats run on the host with
  auto-approved tools and their tool calls are exported. Mitigations: mandates
  forbid printing credentials/environment; `preflight.sh --final` scans the repo
  and history for the real key values; rotate keys after the run.
- **Concurrency limits.** Four seats call the provider at once; rate limits (HTTP
  429) are a failure mode the watchdog does not hide. Check `logs/*.log` after a run.
