# Legacy Band/OpenCode reference

For the current project use the [native Switch setup and verification guide](docs/hackathon-2026/DEMO_RUNBOOK.md).
This file covers only the retained legacy runner. It is not a second Switch
setup guide, a submission demonstration, or production clearance.

## Requirements and limits

Legacy mode needs Band credentials, OpenCode, and its configured inference
provider. `.env.example` documents the optional legacy variables. Native Codex
sign-in and Discord configuration do not belong there.

Host execution is unsafe for untrusted workloads and requires explicit
`FACTORY_ALLOW_UNSAFE_HOST=1`. Same-user tools can bypass prompt restrictions and
read credentials; sanitized environment variables do not establish isolation.
The offline Compose service is a bounded package smoke environment, not a
networked replacement for the native Switch team.

## Deliberate legacy operation

Use a fresh disposable target outside all Factory checkouts. Configure private
`.env` and `agent_config.yaml` locally with permissions 0600; never print or source
the files. The scripts parse their supported key/value configuration themselves.
Read current `--help` output and inspect the dispatch before starting work:

```bash
uv sync --frozen --all-groups --python 3.12
./preflight.sh /absolute/disposable/target
./render-dispatch.sh engineering --task "Inspect this disposable fixture"
```

Only after accepting the host risk, start using the explicit opt-in:

```bash
FACTORY_ALLOW_UNSAFE_HOST=1 RESULT_REPO=/absolute/disposable/target ./start-factory.sh
```

This starts legacy OpenCode/Band processes. It does not start Switch Console or
connect Discord. It uses the autonomous legacy mandates; do not copy them into
native supervised workspaces.

Use `./stop-factory.sh` to stop the owned legacy session. Do not use it to stop
native Switch. Preserve selected evidence outside rolling legacy log retention,
and redact credentials/personal data before sharing logs. PID ownership and
cleanup are checked in source/tests; escaped descendants and same-user host
access remain limitations.

Current results and open issues belong in [BASELINE.md](docs/hackathon-2026/BASELINE.md).
Historical design claims in [the audit ledger](docs/AUDIT.md) and changelog are
not guarantees for a currently running service.
