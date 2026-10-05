# Pocketful Dark Factory

**Track:** pocketful | **Event:** WeAreDevelopers × BAND "Dark Factory" hackathon

## What this is

An autonomous four-seat software factory built on Band Desktop + OpenCode + Featherless AI.
Given a dispatch message, the factory plans, builds, independently reviews, and adversarially
tests each stage of the pocketful service — a wallet and peer-to-peer payments application.

**Autonomy:** The room log (`band-room-export/room.json`) contains **4 human messages**:
the initial dispatch (09:15 UTC), one identical re-dispatch after a timeout (09:34 UTC),
one "continue" nudge after a ~1 h 55 m stall (12:11 UTC), and one steering note to
Stresser/Inspector/Smith (12:18 UTC). The factory was autonomous within stages;
three extra human messages were required to recover from OpenCode timeouts and a stall.

## Stage Status Table

| Stage | Name | Status | Checks | Notes |
|---|---|---|---|---|
| **Stage 1** | JSON API (Ledger, Transfers, Requests, Splits) | **SHIPPED** | **147/147 PASS** | Complete & isolated container verified |
| **Stage 2** | Browser UI & Authorizations | **DRAFT** | In Progress | Preserved on branch `draft-stage-2` per hackathon rules |
| **Stage 3** | Statements & Corrections | **NOT REACHED** | — | Not started |
| **Stage 4** | Refunds & Batch Operations | **NOT REACHED** | — | Not started |

*Note: Per hackathon submission rules, only completed stages ship on `main`. Stage 2 was in progress at cutoff and is preserved on branch `draft-stage-2`.*

## Repository layout

| Path | Purpose |
|---|---|
| `stage-1/` | Stage 1 service (built by the band: `main.py`, `Dockerfile`, `RUN.md`) |
| `FACTORY.md` | Full factory documentation (seats, setup, design, costs) |
| `mandates/` | One mandate per seat: `foreman.md`, `smith.md`, `inspector.md`, `stresser.md` |
| `factory/` | Tooling that runs the seats (start/stop, dispatch renderer, preflight, room analyzer) |
| `band-room-export/` | Full Band room download (`room.json`) — collaboration evidence |
| `task/` | Track task brief and dispatch templates |
| `SUBMISSION_CHECKLIST.md` | Complete verification evidence and requirement matrix |
| `submission-drafts/` | Submission text (`form.md`) and video presentation script (HUMAN-TODO: `video-script.md` not yet written) |

## Build and Run Stage 1

### Build the Docker container

```sh
docker build -t pocketful-s1 ./stage-1
```

### Run under hackathon constraints (isolated network, resource caps)

```sh
docker run -d --rm --network none --cpus=2 --memory=2048m -p 8080:8080 --name pocketful-s1 pocketful-s1
```

### Verify service

```sh
# Health check
curl -s http://localhost:8080/health
# Output: {"status":"ok"}

# Reset with initial state (a valid fixture with at least one user field)
# Note: POST /_test/reset returns 204 No Content on success (no body).
# An empty-body or missing-currency request returns 400 malformed_request.
curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" \
  -d '{"currency":"EUR","minor_units":2,"users":[]}' http://localhost:8080/_test/reset
# Output: 204
```

### Stop container

```sh
docker stop pocketful-s1
```

## Run the Test Harness

```sh
# From the repository root (with dark-factory-wearedevs/.venv activated):
python -m harness check . --track pocketful
python -m harness run --track pocketful --repo . --all --mode isolated
```

## Track

**pocketful** — a wallet and payments service. Money only moves between existing wallets;
balances always sum to the seeded total.
