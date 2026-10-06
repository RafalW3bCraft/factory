# Dark Factory — Factory Tooling

This directory contains the operator-side tools for the WeAreDevelopers × BAND
Dark Factory entry. The four seats write product code into a separate Git
repository named by `RESULT_REPO`.

> These scripts are not a one-click Replit app. They require BAND Desktop and
> seat configuration, OpenCode, a Featherless API key, `uv`, Git, and access
> to the event's separate kickoff harness. Never commit `.env` or
> `agent_config.yaml`.

## Quick reference

| Script | Purpose |
|---|---|
| `start-factory.sh` | Check mandates, then start OpenCode and the four seats |
| `render-dispatch.sh <track> [--stages N]` | Render a dispatch for BAND Desktop |
| `package-submission.sh <repo>` | Copy tooling and mandates into the result repository |
| `stop-factory.sh` | Stop processes started by this factory |
| `bootstrap-repo.sh <path>` | Create a clean result Git repository |
| `preflight.sh <repo> [--final]` | Fresh-clone and run submission checks |
| `src/analyze_room.py` | Summarize room messages and stage timing |
| `src/lint_mandates.py` | Check mandates for track-specific details |

| File/Dir | Purpose |
|---|---|
| `src/run_seat.py` | Launch one seat after checking its mandate |
| `mandates/` | Operating instructions for each seat |
| `dispatch/` | Dispatch messages to paste to Foreman in Band Desktop |
| `templates/` | FACTORY.md and README.md templates for the result repo |
| `RUNBOOK.md` | Ordered runbook: smoke test → toy loop → final run → post-run |
| `agent_config.yaml` | Local BAND seat configuration (not included; never commit) |
| `.env` | Local API key and paths copied from `.env.example` (never commit) |

## Prerequisites

- Python 3.12 and `uv`
- Git and `curl`
- OpenCode installed and available on `PATH`
- BAND Desktop and a valid `agent_config.yaml`
- A Featherless API key
- The event kickoff repository, with its `harness` module installed
- Docker for isolated harness runs

## Install and configure

Run the commands from this directory (`factory/` in this packaged result
repository; a source checkout may nest the same tools at `factory/factory/`):

```sh
uv sync
chmod +x ./*.sh
cp .env.example .env
chmod 600 .env
```

Edit `.env` locally to set `FEATHERLESS_API_KEY` and an **absolute**
`RESULT_REPO` path. Set `HARNESS_REPO` to the local checkout of the event
kickoff repository before running `preflight.sh`. Create `agent_config.yaml`
from the BAND setup instructions; it is intentionally not included in this
import. Keep both files private and out of version control.

## Start a run

Create a result repository once, then start the factory:

```sh
./bootstrap-repo.sh "$HOME/pocketful-result"
RESULT_REPO="$HOME/pocketful-result" ./start-factory.sh
```

In a new BAND Desktop room, paste the output of:

```sh
./render-dispatch.sh pocketful --stages 1
```

After the run, stop the factory with `./stop-factory.sh`. Read `RUNBOOK.md`
before a real run; it covers rehearsal, submission packaging, and checks.
