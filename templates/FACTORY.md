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

### Prerequisites

- Linux (tested: Arch Linux, kernel 7.x)
- `uv` ≥ 0.12 (`curl -fsSL https://astral.sh/uv/install.sh | sh`)
- `opencode` ≥ 1.18 (`curl -fsSL https://opencode.ai/install | bash`)
- Docker daemon running and accessible to your user (`docker info` must work)
- Python 3.12+ (handled automatically by `uv`)
- A Band Desktop account with four seats registered:
  **Foreman**, **Smith**, **Inspector**, **Stresser**
- A Featherless AI API key

### Step 1 — Clone the kickoff package

```sh
git clone <kickoff-repo> ~/band-work/dark-factory-wearedevs
```

### Step 2 — Clone this factory

```sh
git clone <this-repo> ~/band-work/factory-repo
# or use the factory/ directory you already have
```

### Step 3 — Install dependencies

```sh
cd ~/band-work/factory
uv sync          # installs band-sdk[opencode] into .venv at Python 3.12
```

### Step 4 — Configure secrets

Create `~/band-work/factory/.env`:

```sh
FEATHERLESS_API_KEY=<your-key>
RESULT_REPO=/home/<you>/band-work/result
```

Secure it:

```sh
chmod 600 ~/band-work/factory/.env
```

**Never commit `.env` or `agent_config.yaml`.**

### Step 5 — Configure opencode

Write `~/.config/opencode/opencode.json` (not in the result repo):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "featherless": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Featherless AI",
      "options": {
        "baseURL": "https://api.featherless.ai/v1",
        "apiKey": "{env:FEATHERLESS_API_KEY}"
      },
      "models": {
        "zai-org/GLM-5.3-Flash": {}
      }
    }
  }
}
```

### Step 6 — Register seats in Band Desktop

In Band Desktop, create four seats named exactly:
**Foreman**, **Smith**, **Inspector**, **Stresser**.
Set each to OpenCode harness with the `featherless` provider and
`zai-org/GLM-5.3-Flash` model. The `agent_config.yaml` in `factory/` maps
role keys to agent IDs — update it if you re-register seats.

### Step 7 — Bootstrap the result repository

```sh
cd ~/band-work/factory
./bootstrap-repo.sh /home/<you>/band-work/result
```

### Step 8 — Set Docker group (if needed)

If `docker info` fails with permission denied:

```sh
sudo usermod -aG docker $USER
# log out and back in, or: newgrp docker
```

### Step 9 — Run the harness venv

```sh
cd ~/band-work/dark-factory-wearedevs
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r harness/requirements.txt
python -m playwright install chromium
```

### Step 10 — Start the factory

```sh
cd ~/band-work/factory
export RESULT_REPO=/home/<you>/band-work/result
./start-factory.sh
```

In a separate terminal, send the dispatch message to **Foreman** in Band Desktop
(copy from `factory/dispatch/pocketful-all-stages.md`).

### Stop the factory

```sh
./stop-factory.sh
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

---

## Measured time and model spend per stage

| Stage | Wall-clock start | Wall-clock end | Duration | Model spend |
|---|---|---|---|---|
| 1 | TBD | TBD | TBD | TBD |
| 2 | TBD | TBD | TBD | TBD |
| 3 | TBD | TBD | TBD | TBD |
| 4 | TBD | TBD | TBD | TBD |

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
- **Single model, single provider.** All four seats use the same model and
  provider. A Featherless outage halts the factory. Mitigation: the
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
