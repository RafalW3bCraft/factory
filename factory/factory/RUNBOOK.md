# Factory Runbook

**Track:** pocketful | **Submission deadline:** Mon Oct 5 23:59 PDT (= Tue Oct 6 02:59 EDT = Tue Oct 6 12:29 IST).
The lablab page header also shows "Oct 5, 2:59 AM EDT"; the schedule and the event text say
Oct 6 02:59 EDT. Confirm on the submission page and plan against the EARLIER reading if unsure.

This runbook is the ordered list of exact actions to take. Execute each step
and verify it before moving to the next. Do not run the factory without your
go-ahead on steps marked **⚠ COSTS CREDITS**.

---

## Phase 0 — One-time environment setup

Run these once before any factory use.

```sh
# 1. Docker group (open a new shell after this)
sudo usermod -aG docker $USER
newgrp docker
docker info    # must show Server: section without permission error

# 2. Playwright browser deps (for stage-2 harness checks)
source /home/sp3ct0r/band-work/dark-factory-wearedevs/.venv/bin/activate
python -m playwright install --with-deps chromium
deactivate

# 3. Make scripts executable
chmod +x /home/sp3ct0r/band-work/factory/start-factory.sh \
         /home/sp3ct0r/band-work/factory/stop-factory.sh \
         /home/sp3ct0r/band-work/factory/bootstrap-repo.sh \
         /home/sp3ct0r/band-work/factory/preflight.sh
```

---

## Phase 1 — Scratch smoke test (two seats exchange @handle messages)

Purpose: verify Band SDK connectivity, seat registration, and bidirectional
@handle messaging before any real work.

```sh
# Terminal A — start opencode server
cd /home/sp3ct0r/band-work/factory
source .env
opencode serve --hostname=127.0.0.1 --port=4096
```

```sh
# Terminal B — start Foreman seat
cd /home/sp3ct0r/band-work/factory
export RESULT_REPO=/home/sp3ct0r/band-work/scratch-result
./bootstrap-repo.sh "$RESULT_REPO"
uv run python src/run_seat.py foreman zai-org/GLM-5.3-Flash \
  2>&1 | tee logs/smoke-foreman.log
```

```sh
# Terminal C — start Smith seat
cd /home/sp3ct0r/band-work/factory
uv run python src/run_seat.py smith zai-org/GLM-5.3-Flash \
  2>&1 | tee logs/smoke-smith.log
```

In Band Desktop, open the room where both Foreman and Smith are participants.
Send Foreman: `@Smith say hello back to me`.
Verify:
- Foreman sends a message containing `@Smith` 
- Smith replies with a message containing `@Foreman`
- Both messages appear in the room log

**Gate 2 requires reciprocal @handle messages in the SUBMITTED run, not
this smoke test. This is just connectivity validation.**

Stop both seats (Ctrl-C) and the opencode server.

### Phase 1b — Four-seat gate (do not skip; the smoke test above only uses two)

All four seats call Featherless at once in the real run, so rate limits / concurrency
caps only show up now.

```sh
cd /home/sp3ct0r/band-work/factory
export RESULT_REPO=/home/sp3ct0r/band-work/scratch-result
./start-factory.sh        # lints mandates, prints each seat's model, exits non-zero if a seat is down
```

In a scratch room, ask Foreman: `@Smith @Inspector @Stresser each reply to me once, then say done`.
Pass = three replies, no HTTP 429 / timeout in `logs/*.log`. Then `./stop-factory.sh`.

**Choose the Inspector's model now** (reviewer independence): list what your key can use with
`curl -s https://api.featherless.ai/v1/models -H "Authorization: Bearer $FEATHERLESS_API_KEY" | python3 -m json.tool | grep '"id"'`,
pick a different family from the builder, add it to `opencode.json`, and set `Model:` in
`mandates/inspector.md`. `start-factory.sh` picks it up automatically.

---

## Phase 2 — Toy loop (recommended: stage 1 only if time is short)

Time-saver: `./render-dispatch.sh toy --stages 1` renders a stage-1-only dispatch. A stage-1 toy run exercises
every moving part (room, handoffs, export, `harness check`, preflight) in a fraction of the time.

Purpose: rehearse the complete pipeline on the toy track (unscored).

### 2a. Bootstrap toy result repo

```sh
/home/sp3ct0r/band-work/factory/bootstrap-repo.sh \
  /home/sp3ct0r/band-work/toy-result
```

Optionally seed the scaffold into stage-1/ as a starting service (answers `/health`
and `/_test/reset` only — the band writes the rest). **Note: scaffold has no
RUN.md; Smith must write it.**

```sh
mkdir -p /home/sp3ct0r/band-work/toy-result/stage-1
cp /home/sp3ct0r/band-work/dark-factory-wearedevs/scaffold/* \
   /home/sp3ct0r/band-work/toy-result/stage-1/
git -C /home/sp3ct0r/band-work/toy-result \
    -c user.name="factory-bootstrap" \
    -c user.email="factory-bootstrap@factory.invalid" \
    add stage-1/
git -C /home/sp3ct0r/band-work/toy-result \
    -c user.name="factory-bootstrap" \
    -c user.email="factory-bootstrap@factory.invalid" \
    commit -m "chore: add scaffold to stage-1 (Smith must add RUN.md and implement endpoints)"
```

### 2b. Start the factory for the toy run  ⚠ COSTS CREDITS

```sh
cd /home/sp3ct0r/band-work/factory
export RESULT_REPO=/home/sp3ct0r/band-work/toy-result
./start-factory.sh
```

In Band Desktop, send Foreman the output of:
`./render-dispatch.sh toy` (or `--stages 1`)

Wait for Foreman's final report. Stop the factory:

```sh
./stop-factory.sh
```

### 2c. Check each stage

```sh
source /home/sp3ct0r/band-work/dark-factory-wearedevs/.venv/bin/activate

for N in 1 2 3 4; do
  python -m harness run --track toy \
    --repo /home/sp3ct0r/band-work/toy-result \
    --stage $N \
    --out /home/sp3ct0r/band-work/checks/toy-s${N}-$(date +%Y%m%d-%H%M%S)
done
```

Expected: `claimed stage: N` for each N. The extra `fail` line for the next
suite is normal.

### 2d. Download room.json and run harness check

In Band Desktop:
1. Open the toy room → ⋮ menu → Open in Band console
2. Download full session → save as `room.json`

```sh
mv ~/Downloads/<room-name>.json /home/sp3ct0r/band-work/toy-result/room.json
python -m harness check /home/sp3ct0r/band-work/toy-result --track toy
```

Fix any issues reported. This verifies gates 1 and 2 on the toy before they
matter on the real repo.

---

## Phase 3 — Final run (fresh room, fresh repo) ⚠ COSTS CREDITS

This is the run that gets submitted. Do this only when the toy loop passes
and mandates are validated.

### 3a. Create a fresh Band room

In Band Desktop: create a **new room** named (e.g.) "Pocketful Factory".
Do NOT reuse the toy room or any development room.

### 3b. Bootstrap a fresh result repo

```sh
/home/sp3ct0r/band-work/factory/bootstrap-repo.sh \
  /home/sp3ct0r/band-work/result-final
```

`bootstrap-repo.sh` already copied `mandates/` and the `FACTORY.md`/`README.md` skeletons and committed them.
Nothing more to do here.

### 3c. Start the factory

```sh
cd /home/sp3ct0r/band-work/factory
export RESULT_REPO=/home/sp3ct0r/band-work/result-final
./start-factory.sh
```

### 3d. Dispatch

Start screen recording NOW (OBS; see PLAN.md for low-fps settings), then in Band Desktop (in the **new room**)
send Foreman the complete output of:

```sh
./render-dispatch.sh pocketful          # add --stages 2 if time is short
```

The rendered message uses `$RESULT_REPO`, so the seats cannot build in a different directory
than the one that gets submitted.

This is the **only** human input for the entire run. Do not send any other
message (no "looks good", no reruns, no hints) until Foreman posts the final
stage-4 report.

### 3e. Monitor

Watch `logs/foreman.log`, `logs/smith.log`, `logs/inspector.log`,
`logs/stresser.log`. The factory is autonomous; let it run.

### 3f. Stop the factory

```sh
./stop-factory.sh
```

---

## Phase 4 — Post-run: verify, fill numbers, video

### 4a. Package, then run the final preflight

If the run was cut off mid-stage, delete the incomplete `stage-K/` first
(`git rm -r stage-K`, commit as factory-bootstrap) and disclose it in FACTORY.md.

```sh
./package-submission.sh /home/sp3ct0r/band-work/result-final   # tooling + mandates into the repo
./preflight.sh /home/sp3ct0r/band-work/result-final --final
```

Fix every issue reported. Repeat until it passes.

Also run the isolated harness run manually to double-check:

```sh
source /home/sp3ct0r/band-work/dark-factory-wearedevs/.venv/bin/activate
python -m harness run --track pocketful \
  --repo /home/sp3ct0r/band-work/result-final \
  --all \
  --mode isolated \
  --out /home/sp3ct0r/band-work/checks/final-$(date +%Y%m%d-%H%M%S)
```

### 4b. Fill FACTORY.md numbers

```sh
# Start time
cat /home/sp3ct0r/band-work/factory/logs/started_at

# End time: last timestamp in room.json
python3 -c "
import json, sys
data = json.load(open('/home/sp3ct0r/band-work/result-final/room.json'))
events = data.get('events', data.get('messages', []))
ts = [e.get('created_at') or e.get('timestamp','') for e in events]
ts = [t for t in ts if t]
print('Last event:', max(ts) if ts else 'n/a')
"

# Spend: go to https://platform.featherless.ai → Subscription → Usage
# Filter to the run dates, note the total.
```

Get the numbers (human-message count, per-stage report times, rejections, commit authors):

```sh
python src/analyze_room.py /home/sp3ct0r/band-work/result-final/room.json --repo /home/sp3ct0r/band-work/result-final
```

Edit `result-final/FACTORY.md`: fill the Stage table, the run-facts table and the two "bad work caught"
examples (`--final` preflight fails while any `TBD` remains).

### 4c. Download room.json

In Band Desktop:
1. Open the **final pocketful room** → ⋮ → Open in Band console
2. Download full session (not filtered)
3. Rename and place:

```sh
mv ~/Downloads/<room>.json /home/sp3ct0r/band-work/result-final/room.json
git -C /home/sp3ct0r/band-work/result-final \
    -c user.name="factory-bootstrap" \
    -c user.email="factory-bootstrap@factory.invalid" \
    add room.json FACTORY.md
git -C /home/sp3ct0r/band-work/result-final \
    -c user.name="factory-bootstrap" \
    -c user.email="factory-bootstrap@factory.invalid" \
    commit -m "chore: add room.json and fill FACTORY.md costs"
```

### 4d. Final harness check

```sh
python -m harness check /home/sp3ct0r/band-work/result-final --track pocketful
```

Must pass with no errors.

### 4e. Read room.json for credentials

```sh
python3 -c "
import json, re
data = open('/home/sp3ct0r/band-work/result-final/room.json').read()
patterns = [
    r'AKIA[A-Z0-9]{16}',
    r'ghp_[A-Za-z0-9]{36}',
    r'sk-[A-Za-z0-9]{32,}',
    r'band_[a-zA-Z0-9_]{20,}',
]
for p in patterns:
    hits = re.findall(p, data)
    if hits:
        print(f'FOUND pattern {p}: {len(hits)} matches — rotate and redact')
print('Scan complete.')
"
```

If any credential pattern is found: **rotate the credential first**, then
replace the value in `room.json` with `[REDACTED]`.

### 4f. Push to GitHub

```sh
git -C /home/sp3ct0r/band-work/result-final push origin main
```

Verify the push is public and clonable without Band Desktop membership.

### 4g. Video checklist

The video must include (guide requirement: "the room, a handoff between
seats, and the result it produced"):

- [ ] Screen recording of the Band Desktop room showing messages between at
      least two seats with @handle addressing in both directions
- [ ] A handoff message: Foreman → Smith, and Smith → Inspector (both visible)
- [ ] Inspector's response (accept or reject with evidence)
- [ ] The result repository: at minimum `stage-1/` building and passing
      `harness run --stage 1`
- [ ] `FACTORY.md` open in an editor (shows the stand-it-up instructions)
- [ ] Walkthrough narration explaining: factory design, a bad result it
      caught, and the stage reached

Record with OBS or similar. Export as MP4.

### 4h. Submit

Go to the lablab submission page. Submit:
1. GitHub repository URL
2. Presentation (slides)
3. Video (MP4)

Keep the confirmation receipt.

---

## Quick reference: key commands

| Purpose | Command |
|---|---|
| Start factory | `cd ~/band-work/factory && export RESULT_REPO=<path> && ./start-factory.sh` |
| Stop factory | `./stop-factory.sh` |
| Bootstrap repo | `./bootstrap-repo.sh <absolute-path>` |
| Preflight check | `./preflight.sh <repo-path>` |
| Harness check | `python -m harness check <repo> --track pocketful` |
| Harness run (host) | `python -m harness run --track pocketful --repo <repo> --stage N --out <dir>` |
| Harness run (isolated) | `python -m harness run --track pocketful --repo <repo> --all --mode isolated --out <dir>` |
