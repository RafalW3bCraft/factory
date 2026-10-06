# Pocketful Dark Factory

**Track:** pocketful · **Event:** WeAreDevelopers × BAND Dark Factory

Pocketful is a wallet and peer-to-peer payments service built by a four-seat
software factory. The factory uses Foreman, Smith, Inspector, and Stresser to
plan, implement, independently verify, and adversarially test work.

## Project status

| Stage | Scope | Status | Evidence |
|---|---|---|---|
| 1 | Ledger, transfers, requests, splits | Shipped | 147/147 official harness checks passed |
| 2 | Browser UI and authorizations | Not included in `main` | Work was in progress and uncommitted at export |
| 3 | Statements and corrections | Not reached | Not started |
| 4 | Refunds and batch operations | Not reached | Not started |

The room log records **four human messages**, not one: the original dispatch,
a duplicate dispatch after a timeout, a “continue” message after a long stall,
and a later steering note. The run also had three OpenCode timeouts. These
limits are disclosed rather than described as fully autonomous. See
[`docs/FACT_SHEET.md`](docs/FACT_SHEET.md) for the evidence-backed timeline.

## Run Stage 1

The API uses only the Python 3 standard library. From the repository root:

```sh
python3 stage-1/main.py
```

It listens on `0.0.0.0:8080` by default. In another terminal, check health:

```sh
curl -i http://127.0.0.1:8080/health
```

Reset the in-memory service state with a fixture:

```sh
curl -i -X POST http://127.0.0.1:8080/_test/reset \
  -H 'Content-Type: application/json' \
  -d '{"currency":"EUR","minor_units":2,"users":[]}'
```

A successful reset returns **204 No Content**. The state is in memory and is
cleared when the process stops. To use another port, set `PORT` before start,
for example `PORT=9000 python3 stage-1/main.py`.

### Docker

Docker is optional for a local smoke test. To build and run the isolated image:

```sh
docker build -t pocketful-s1 ./stage-1
docker run --rm --network none --cpus=2 --memory=2048m \
  -p 8080:8080 --name pocketful-s1 pocketful-s1
```

The `--network none` option is appropriate for the containerized test run; omit
it if you need to reach the container from a different network namespace.
Stop a detached container with `docker stop pocketful-s1`.

## Test harness

The WeAreDevelopers/BAND kickoff harness is not bundled in this repository.
Install it from the event's kickoff package, then run these commands from its
environment:

```sh
python -m harness check . --track pocketful
python -m harness run --track pocketful --repo . --all --mode isolated
```

The isolated run requires a working Docker daemon. The 147/147 result in this
README is the recorded submission evidence; it is not a claim that the
external harness is installed in every checkout.

## Repository map

| Path | Purpose |
|---|---|
| `stage-1/` | Shipped API, Dockerfile, and run instructions |
| `FACTORY.md` | Factory design, setup, measured results, and limitations |
| `mandates/` | Operating instructions for the four seats |
| `factory/factory/` | Source copy of the factory scripts and runbook |
| `room.json` | Full room export used as collaboration evidence |
| `docs/FACT_SHEET.md` | Audited source of truth for submission claims |
| `submission-assets/` | Form copy, slides, video, scripts, and audit material |

For the Stage 1-specific commands and API behavior, see
[`stage-1/RUN.md`](stage-1/RUN.md). For running the multi-agent factory, start
with [`factory/factory/README.md`](factory/factory/README.md); that workflow
requires separately configured BAND, OpenCode, Featherless, and harness tools.
