# Dark Factory — Factory Tooling

This directory contains the **factory tooling** for the WeAreDevelopers × BAND
"Dark Factory" hackathon entry (track: **pocketful**).

The factory tooling is what you, the human operator, maintain. It starts and
manages the Band seats. The seats produce all product code in `RESULT_REPO`.

## Quick reference

| Script | Purpose |
|---|---|
| `start-factory.sh` | Start `opencode serve` + all 4 seat processes |
| `stop-factory.sh` | Kill only our own processes (PID file based) |
| `bootstrap-repo.sh <path>` | Create a fresh result git repo (no stage content) |
| `preflight.sh <repo>` | Fresh-clone → harness check → isolated harness run → assertions |

| File/Dir | Purpose |
|---|---|
| `src/run_seat.py` | Python: launches one seat (mandate guard + auto-reject questions) |
| `mandates/` | One `.md` per seat (generic; no track-specific vocabulary) |
| `dispatch/` | Dispatch messages to paste to Foreman in Band Desktop |
| `templates/` | FACTORY.md and README.md templates for the result repo |
| `RUNBOOK.md` | Ordered runbook: smoke test → toy loop → final run → post-run |
| `agent_config.yaml` | Band seat IDs and keys (never commit; in .gitignore) |
| `.env` | FEATHERLESS_API_KEY and RESULT_REPO (never commit; chmod 600) |

## Setup (one-time)

```sh
uv sync                          # install band-sdk[opencode] into .venv
chmod +x *.sh
cp .env.example .env             # then fill in your values
chmod 600 .env
```

## Start a run

```sh
export RESULT_REPO=/absolute/path/to/result
./start-factory.sh
# In Band Desktop: paste dispatch/pocketful-all-stages.md → Foreman
# Wait for Foreman's final report, then:
./stop-factory.sh
```

See `RUNBOOK.md` for the full ordered procedure.
