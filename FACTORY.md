# FACTORY.md

> This file is the authoritative description of the **Pocketful Dark Factory**.
> It must be enough for another team to stand the factory up from scratch, without
> any additional explanation from us.

---

## Overview

This factory is a four-seat autonomous software factory built on
[Band Desktop](https://band.ai) with [OpenCode](https://opencode.ai) seats
powered by Featherless AI open-weights models. Given a single dispatch message,
the factory plans, builds, independently reviews, and adversarially tests each
stage of the **pocketful** track without human steering.

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
| `inspector` | Inspector | OpenCode | `zai-org/GLM-5.3-Flash` | See *Stand it up from scratch* |
| `stresser` | Stresser | OpenCode | `zai-org/GLM-5.3-Flash` | See *Stand it up from scratch* |

---

## Stand it up from scratch

Everything needed is in this repository: the seats' standing instructions are in
`mandates/`, the tooling that runs them is in `factory/`.

### Prerequisites

- Linux (tested: Arch Linux, kernel 7.x), `git`, `curl`
- `uv` ≥ 0.12 (`curl -fsSL https://astral.sh/uv/install.sh | sh`)
- `opencode` ≥ 1.18 (`curl -fsSL https://opencode.ai/install | bash`)
- Docker daemon accessible to your user (`docker info` must work)
- A BAND account + BAND Desktop, and a Featherless AI API key
- The hackathon kickoff package (the harness and the track specs)

### Step 1 — Get the kickoff package and this repository

```sh
git clone <kickoff-repo-url> ~/band-work/dark-factory-wearedevs
git clone <this-repo-url>    ~/band-work/submission
cd ~/band-work/submission/factory
```

### Step 2 — Install dependencies

```sh
uv sync          # installs band-sdk[opencode] into factory/.venv (Python 3.12)
chmod +x *.sh
```

### Step 3 — Secrets (never commit these)

```sh
cp .env.example .env && chmod 600 .env     # set FEATHERLESS_API_KEY and RESULT_REPO
```

### Step 4 — Configure OpenCode (outside any repo)

`~/.config/opencode/opencode.json`. **Every `Model:` line in `mandates/*.md` must
appear under `models`** (`./start-factory.sh` prints the model each seat will use):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "featherless": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Featherless AI",
      "options": { "baseURL": "https://api.featherless.ai/v1", "apiKey": "{env:FEATHERLESS_API_KEY}" },
      "models": { "zai-org/GLM-5.3-Flash": {} }
    }
  }
}
```

### Step 5 — Register the four seats in BAND Desktop

Create four external agents named exactly **Foreman**, **Smith**, **Inspector**,
**Stresser**. Save each agent's id and API key into `factory/agent_config.yaml`
under the lowercase role key (`foreman`, `smith`, `inspector`, `stresser`).
Redacted example of the file as read by `band.config.load_agent_config`:

```yaml
foreman:
  agent_id: REDACTED
  api_key: REDACTED
smith:
  agent_id: REDACTED
  api_key: REDACTED
inspector:
  agent_id: REDACTED
  api_key: REDACTED
stresser:
  agent_id: REDACTED
  api_key: REDACTED
```

### Step 6 — Harness environment

```sh
cd ~/band-work/dark-factory-wearedevs
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r harness/requirements.txt
python -m playwright install --with-deps chromium
```

If `docker info` says permission denied: `sudo usermod -aG docker $USER`, then `newgrp docker`.

### Step 7 — Fresh result repository, then start the band

```sh
cd ~/band-work/submission/factory
./bootstrap-repo.sh ~/band-work/result-final        # copies mandates/, templates; no stage content
export RESULT_REPO=~/band-work/result-final
./start-factory.sh        # lints mandates, starts opencode + 4 seats; exits non-zero if any seat is not up
```

### Step 8 — Dispatch (the only human input)

```sh
./render-dispatch.sh pocketful      # prints (and copies) the dispatch with every path resolved
```

Create a **new** room in BAND Desktop, paste the dispatch to **Foreman**, then do
nothing until Foreman's final report. `./stop-factory.sh` stops everything.

### Step 9 — After the run

```sh
./package-submission.sh "$RESULT_REPO"            # copies tooling + mandates into the repo
./preflight.sh "$RESULT_REPO" --final             # fresh clone, harness check, isolated run, secret scan
python src/analyze_room.py "$RESULT_REPO/room.json" --repo "$RESULT_REPO"
```

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
| 1 | ~07:30 UTC | ~10:15 UTC | ~2h 45m | [See billing / room.json] |
| 2 | In progress (draft-stage-2) | — | — | — |
| 3 | Not reached | — | — | — |
| 4 | Not reached | — | — | — |

### Run facts (fill from `analyze_room.py` and `factory/run-evidence/`)

| Fact | Value |
|---|---|
| Human messages in the submitted room (= dispatches) | 1 (Initial Stage 1 dispatch; subsequent autonomous run) |
| Total room messages | [Run `analyze_room.py room.json` after export] |
| Seat restarts (`events.log`) | 1 (`events.log`: OpenCode server timeout / restart) |
| Rejections by Inspector that changed the code | 1 (C1: 0-byte bodies 422->400, commit `5620886`) |
| Defects found by Stresser after acceptance | 0 |
| Highest stage accepted / harness result | Stage 1 accepted (147/147 pass isolated mode) |
| Total model spend | [Sum from Featherless dashboard for run period] |

### Bad work the band caught (from the room; at least two, with revisions)

1. **Incident 1 — 0-byte request bodies returned HTTP 422 instead of HTTP 400 (Revision `ef1a437` rejected):**
   - **Defect:** `parse_json_object` treated an empty request body as an empty JSON dict `{}`. Endpoints with required fields (e.g. `POST /payments`, `POST /auth/login`, `POST /_test/reset`) therefore raised validation failures and returned `422 validation_failed` instead of `400 malformed_request` per API specification §5.
   - **Evidence Produced:** Inspector repro curls on empty POST requests returning HTTP 422 with `validation_failed`.
   - **Fixing Revision:** `5620886` (`fix(stage 1): 0-byte request bodies are 400 malformed_request; init store indexes`). Uniform guard checks for empty body before parsing JSON.
   - **Turns / Resolution:** 1 rework cycle. Inspector re-verified and passed.

2. **Incident 2 — Container cold-start index failure before reset (Revision `ef1a437` rejected during verification):**
   - **Defect:** Initial service state was instantiated without building derived indexes (user ID, handle, email, payment requests). Any call to `POST /auth/signup` or `POST /auth/login` on a fresh container prior to calling `POST /_test/reset` failed with a generic HTTP 400 error.
   - **Evidence Produced:** Inspector fresh-container test (`signup before reset`) failed with HTTP 400.
   - **Fixing Revision:** `5620886`. Store indexes are now explicitly initialized at startup.
   - **Turns / Resolution:** Fixed in `5620886`, verified across fresh container startup checks (`signup` -> 201, `login` -> 200, `/me` -> 200 balance 0).

**How to measure:**
- **Start:** `cat ~/band-work/factory/logs/started_at`
- **End:** last timestamp in `room.json` (the Foreman's final report message)
- **Spend:** Featherless subscription page → Usage, filtered to the run dates,
  summed across all four seats.

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
   Before pushing, run `./preflight.sh ~/band-work/result` to fresh-clone
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
- **Playwright browser tests require system deps.** On Arch Linux, run
  `python -m playwright install --with-deps chromium` once before the harness
  venv is used for stage-2 checks.
- **`harness run --mode isolated` requires Docker daemon access.**
  If Docker permission is denied, add the user to the `docker` group and
  open a new shell (`newgrp docker`).
- **Secrets can leak into the public room export.** Seats run on the host with
  auto-approved tools and their tool calls are exported. Mitigations: mandates
  forbid printing credentials/environment; `preflight.sh --final` scans the repo
  and history for the real key values; rotate keys after the run.
- **Concurrency limits.** Four seats call the provider at once; rate limits (HTTP
  429) are a failure mode the watchdog does not hide. Check `logs/*.log` after a run.
