# Pocketful Dark Factory

**Track:** pocketful | **Event:** WeAreDevelopers × BAND "Dark Factory" hackathon

## What this is

A four-seat software factory built on Band Desktop + OpenCode + Featherless AI.
After a human dispatch, the factory plans, builds, independently reviews, and
adversarially tests the work. Record every later human message and timeout in
the submission account; do not claim a single-dispatch run unless the room
export shows that.

## Repository layout

| Path | Purpose |
|---|---|
| `FACTORY.md` | Factory documentation (seats, setup, design, measured results) |
| `mandates/` | One mandate per seat: `foreman.md`, `smith.md`, `inspector.md`, `stresser.md` |
| `factory/` | Tooling that runs the seats (start/stop, dispatch renderer, preflight, room analyzer) |
| `room.json` | Full Band room download — the collaboration evidence |
| `stage-N/` | Product code for each stage the band actually committed |

Only committed `stage-N/` directories are part of the submission. Do not list
uncommitted working-tree work as shipped.

## Quick harness check

```sh
# From the repo root (requires the event kickoff harness installed)
python -m harness check . --track pocketful
python -m harness run --track pocketful --repo . --all --mode isolated \
  --out ../checks/final-$(date +%Y%m%d-%H%M%S)
```

## Stand it up

See `FACTORY.md → Stand it up from scratch` for the complete setup
instructions. The factory runs on Linux with `uv`, `opencode` and Docker
installed.

## Track

**pocketful** — a wallet and payments service. Money only moves between
existing wallets; balances always sum to the seeded total. Four stages:
JSON API → browser UI + authorizations → statements + corrections →
refunds + batch corrections.
