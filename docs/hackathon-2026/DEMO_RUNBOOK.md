# FactoryOps Live Demo Runbook

This runbook is for the real Switch/Discord demonstration. It does not claim
that Switch Console, Discord, or any agent has been configured until those
interactive steps have actually completed.

## 1. Local preparation

From the `flip-the-switch-2026` worktree, install the locked development
environment and create a new disposable directory outside every Factory
checkout:

```bash
uv sync --frozen --all-groups
uv run factoryops init-demo --root /absolute/new/factoryops-demo
```

Keep the JSON output. It identifies the fixture repository and the Builder,
Inspector, and Stresser worktrees. The fixture starts with one intentional
defect: it accepts a negative restock amount and decreases inventory.

## 2. Create the native Switch team

1. In Switch Console, ensure the local Codex provider is installed and signed
   in, then connect the intended Discord account and link the human operator.
2. Import `switch/factoryops.template.yaml` on the Templates page.
3. Select a unique team prefix and the connected Discord bridge. Keep provider
   as `codex`; do not enable automatic approval.
4. Set `demo_root` to the directory created above. Set `foreman_directory` to
   this FactoryOps event worktree. Set the other three directory fields to the
   matching paths emitted by `init-demo`.
5. Create the team. Console must confirm all four agents and the Discord room
   were created. Capture any setup failure as a blocker instead of substituting
   mock messages.

## 3. Run the governed workflow

The linked human sends an explicitly addressed Discord report such as:

```text
@factoryops-foreman Restock accepts -1 and silently lowers inventory. Please investigate and fix it.
```

Expected observable sequence:

1. Foreman posts a `DEFECT-*` triage and a self-contained Smith handoff.
2. Smith adds a regression test, reports the actual RED result, fixes the
   fixture, runs `python -m unittest discover -s tests`, commits, and posts the
   complete candidate SHA.
3. Foreman prepares each verifier at exactly that SHA:

   ```bash
   uv run factoryops prepare-verifier --root /absolute/new/factoryops-demo --role inspector --commit <40-char-sha>
   uv run factoryops prepare-verifier --root /absolute/new/factoryops-demo --role stresser --commit <40-char-sha>
   ```

4. Inspector independently reports its static verdict. Stresser independently
   runs only local fixture probes and reports its dynamic verdict.
5. Foreman requests approval only after both verdicts pass. The linked human
   replies in ordinary language, for example: `Looks good — please publish the
   completion report.`
6. Foreman echoes the candidate SHA, linked human identity, request timestamp,
   response timestamp, and approval text before posting the final report.

Do not merge, deploy, or push the disposable fixture repository. The required
real change is Smith's local, verifiable fixture commit.

## 4. Evidence and release gate

Collect the actual Discord/Switch room export or screenshots, the seeded and
candidate commit SHAs, and copied command output with exit codes. Redact any
credentials, Discord tokens, private room URLs, or unrelated personal data.
Only then fill `LIVE_DEMO_EVIDENCE.md`; do not manufacture a transcript.

The FactoryOps event branch may be non-force pushed only after the local
verification suite and this live workflow both pass. Never merge it into
`main` or `hardening/prod-ready` as part of the hackathon demo.
