# Factory Runbook

This guide applies to the source checkout (`factory/factory/`) and to a
packaged result repo (`factory/`). It uses paths discovered from the checkout
instead of paths tied to one workstation.

## 1. Set up paths

From the repository root:

```sh
export REPO_ROOT="$(git rev-parse --show-toplevel)"
if [ -f "$REPO_ROOT/factory/factory/pyproject.toml" ]; then
  export FACTORY_DIR="$REPO_ROOT/factory/factory"
else
  export FACTORY_DIR="$REPO_ROOT/factory"
fi
export WORK_ROOT="${WORK_ROOT:-$(dirname "$REPO_ROOT")}"
export HARNESS_REPO="${HARNESS_REPO:-$WORK_ROOT/dark-factory-wearedevs}"
export RESULT_REPO="${RESULT_REPO:-$WORK_ROOT/result-final}"
export CHECKS_DIR="${CHECKS_DIR:-$WORK_ROOT/checks}"
```

If the kickoff repository is somewhere else, set `HARNESS_REPO` to its
absolute path. The kickoff harness is not included in this project.

## 2. Install and configure the tools

Required: Python 3.12, `uv`, Git, `curl`, OpenCode, BAND Desktop, a Featherless
API key, the event kickoff harness, and Docker for isolated harness checks.

```sh
cd "$FACTORY_DIR"
uv sync
chmod +x ./*.sh
cp .env.example .env
chmod 600 .env
```

Edit `.env` locally. Set `FEATHERLESS_API_KEY` and an absolute `RESULT_REPO`
path. Keep `.env` and `agent_config.yaml` private and out of Git. Register the
four BAND agents as **Foreman**, **Smith**, **Inspector**, and **Stresser**;
create `agent_config.yaml` using the BAND SDK's required format. It is
intentionally not included in this import.

Configure OpenCode with the Featherless provider and the model IDs in the
`Model:` lines of `mandates/*.md`. Install the event harness using its own
instructions, then check:

```sh
cd "$HARNESS_REPO"
python -m harness --help
docker info
```

Open a new terminal? Re-run the path setup in section 1. For preflight checks,
export the paths in that shell and load the local configuration if needed:

```sh
cd "$FACTORY_DIR"
set -a
. ./.env
set +a
export HARNESS_REPO CHECKS_DIR
```

## 3. Rehearse without dispatching a real task

Do not run the paid four-seat factory just to test installation. First check
the local setup and mandate lint:

```sh
cd "$FACTORY_DIR"
uv run python src/lint_mandates.py
./start-factory.sh
```

`start-factory.sh` checks the BAND configuration, Featherless key, target Git
repository, and seat startup before it is ready for a dispatch. Starting seats
can consume provider credits. Do not send a dispatch until all four seats pass
the startup gate.

## 4. Run the Stage 1 dispatch

For a real run, use a fresh BAND room and a fresh result repository. Create the
repository only if it does not already exist:

```sh
cd "$FACTORY_DIR"
./bootstrap-repo.sh "$RESULT_REPO"
```

Start the seats:

```sh
./start-factory.sh
```

In the new BAND room, send Foreman the Stage 1 task rendered by:

```sh
./render-dispatch.sh pocketful --stages 1
```

Monitor `logs/*.log`. When the run is complete, stop only this factory's
processes:

```sh
./stop-factory.sh
```

Record every human message, timeout, and recovery action accurately. The
submitted room had four human messages, three OpenCode timeouts, and a
roughly 1 hour 55 minute stall; it was not a single-dispatch run.

## 5. Package and verify

Download the full BAND room export to `$RESULT_REPO/room.json`, then run:

```sh
cd "$FACTORY_DIR"
./package-submission.sh "$RESULT_REPO"
python src/analyze_room.py "$RESULT_REPO/room.json" --repo "$RESULT_REPO"
./preflight.sh "$RESULT_REPO"
```

The final preflight runs from a fresh clone and requires the event harness and
Docker. After resolving its warnings and confirming all intended files are
committed, run:

```sh
./preflight.sh "$RESULT_REPO" --final
```

For a manual isolated harness run:

```sh
mkdir -p "$CHECKS_DIR"
python -m harness check "$RESULT_REPO" --track pocketful
python -m harness run --track pocketful --repo "$RESULT_REPO" \
  --all --mode isolated --out "$CHECKS_DIR/final"
```

The official harness is external to this repository. A missing `harness`
module means the kickoff package or its Python environment is not set up; it
does not mean the Pocketful API itself failed.

## 6. Before sharing the submission

- Check that `room.json`, `FACTORY.md`, `README.md`, and the stage run guide
  agree on the shipped stage and human-intervention count.
- Review screen recordings and exports for credentials, account details, and
  machine-specific paths. Rotate any credential that was exposed; a visual
  redaction alone does not revoke a key.
- Run `preflight.sh --final` after the final commit.
- Submit the repository, required slides, and the redacted presentation video.

## Troubleshooting

| Message or symptom | Action |
|---|---|
| `factory virtualenv python not found` | Run `uv sync` from `$FACTORY_DIR`. |
| `agent_config.yaml missing` | Configure BAND locally; do not commit the file. |
| `FEATHERLESS_API_KEY is empty` | Set it in the private `.env` file. |
| Harness import or command fails | Set up the kickoff repo at `$HARNESS_REPO` and use its environment. |
| Docker permission error | Start Docker and grant the current account permission to use its daemon. |
| Seat startup gate fails | Stop before dispatch; inspect `logs/opencode.log` and `logs/<seat>.log`. |
