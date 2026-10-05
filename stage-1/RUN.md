# Pocketful — Stage 1

Containerized HTTP service. Single process, Python 3 standard library only,
in-memory state. Listens on `0.0.0.0` using the `PORT` environment variable
(default `8080`). No runtime dependencies beyond the base image; no outbound
network access is needed at runtime.

## Build

```sh
docker build -t pocketful-s1 /home/sp3ct0r/band-work/result-final/stage-1
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
curl -s http://localhost:8080/health
# expect: {"status":"ok"}
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