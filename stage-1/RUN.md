# Pocketful — Stage 1

Containerized HTTP service. Single process, Python 3 standard library only,
in-memory state. Listens on `0.0.0.0` using the `PORT` environment variable
(default `8080`). No runtime dependencies beyond the base image; no outbound
network access is needed at runtime.

## Run directly (no Docker)

From the repository root:

```sh
python3 stage-1/main.py
```

In another terminal, verify the health endpoint:

```sh
curl -i http://127.0.0.1:8080/health
```

Stop the process with `Ctrl-C`. Set `PORT` to listen on another port.

## Build

Run this from the repository root:

```sh
docker build -t pocketful-s1 ./stage-1
```

## Run

```sh
docker run -d --rm -p 8080:8080 --name pocketful-s1 pocketful-s1
```

To use a different port, map it and set `PORT`:

```sh
docker run -d --rm -e PORT=9000 -p 8080:9000 --name pocketful-s1 pocketful-s1
```

## Verify

```sh
curl -i http://127.0.0.1:8080/health
# expect HTTP 200 and {"status":"ok"}

curl -i -X POST http://127.0.0.1:8080/_test/reset \
  -H 'Content-Type: application/json' \
  -d '{"currency":"EUR","minor_units":2,"users":[]}'
# expect HTTP 204 No Content (an empty response body)
```

## Stop

```sh
docker stop pocketful-s1
```

## Notes

- The service is ready as soon as `GET /health` answers; there is no
  initialization delay.
- State is in memory and seeded exclusively through `POST /_test/reset`
  (see the stage 1 specification, §3.3 and §4). It does not survive a
  container restart, which is expected.
- All responses are `application/json; charset=utf-8`.
- The official event harness is external to this repository. Its check/run
  commands require that kickoff package and, for isolated runs, Docker.