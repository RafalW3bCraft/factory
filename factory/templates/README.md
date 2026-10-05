# Pocketful Dark Factory

**Track:** pocketful | **Event:** WeAreDevelopers × BAND "Dark Factory" hackathon

## What this is

An autonomous four-seat software factory built on Band Desktop + OpenCode +
Featherless AI. Given a single dispatch message, the factory plans, builds,
reviews and adversarially tests each stage of the pocketful service — a
wallet and peer-to-peer payments application — without any human steering
after the initial dispatch.

## Repository layout

| Path | Purpose |
|---|---|
| `FACTORY.md` | Full factory documentation (seats, setup, design, costs) |
| `mandates/` | One mandate per seat: `foreman.md`, `smith.md`, `inspector.md`, `stresser.md` |
| `factory/` | The tooling that runs the seats (start/stop, dispatch renderer, preflight, room analyzer) |
| `room.json` | Full Band room download — the collaboration evidence |
| `stage-1/` | Stage 1 service (built by the band) |
| `stage-2/` | Stage 2 service (built by the band) |
| `stage-3/` | Stage 3 service (built by the band) |
| `stage-4/` | Stage 4 service (built by the band) |

## Quick harness check

```sh
# From the repo root (requires dark-factory-wearedevs/.venv activated)
python -m harness check . --track pocketful
python -m harness run --track pocketful --repo . --all --mode isolated \
  --out ../checks/final-$(date +%Y%m%d-%H%M%S)
```

## Stand it up

See `FACTORY.md → Stand it up from scratch` for the complete, copy-paste
setup instructions. The factory runs on Linux with `uv`, `opencode` and
Docker installed.

## Track

**pocketful** — a wallet and payments service. Money only moves between
existing wallets; balances always sum to the seeded total. Four stages:
JSON API → browser UI + authorizations → statements + corrections →
refunds + batch corrections.
