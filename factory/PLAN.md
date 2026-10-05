# PLAN — finish and submit (pocketful track)

Not part of the submitted repo (`package-submission.sh` does not copy it).

## 0. Where you actually stand

- This zip is the **factory tooling only**. It contains no `stage-N/`, no `room.json`, no measured
  numbers, no video, no deck. Everything the judges score (Factory 50 / App 25 / Teamwork 25) comes from
  **a run that has to happen**. No code can substitute for that run, and the rules forbid hand-writing
  the product code ("code traces to the room").
- **Deadline:** Mon Oct 5 23:59 PDT = Tue Oct 6 02:59 EDT = **Tue Oct 6 12:29 IST**. The lablab page
  header says "Oct 5, 2:59 AM EDT", which contradicts its own schedule. Open the submission page and
  read its countdown. If in doubt, plan against the earlier reading.
- Working unit below: **T−Nh = N hours before the deadline.**

## 1. What I changed in the tooling (all tested here except where noted)

| # | Problem found | Fix |
|---|---|---|
| 1 | **Dispatch hard-coded `/band-work/result`; the runbook's final run uses `result-final`.** Seats would have built in a different directory than the one submitted, and `preflight.sh` would only warn "no stage folders". | Dispatches are templates; `./render-dispatch.sh pocketful [--stages N]` fills every path from `RESULT_REPO` and fails on unresolved tokens. |
| 2 | `start-factory.sh` forced one `$MODEL` on all seats (its header says per-seat). A different-model reviewer was impossible; a seat dying at startup still printed "All seats running". `/api/health` is unverified. | Model read from each mandate; startup gate (all seats alive ~15 s or exit 1 *before* you dispatch); multi-path readiness with port fallback; bounded crash-restart watchdog → `logs/events.log`; mandate lint before start. |
| 3 | `stop-factory.sh` killed seats before the supervisor. | Supervisor first. |
| 4 | `run_seat.py` hid tracebacks, fixed 900 s turn timeout. | Tracebacks; `TURN_TIMEOUT_S`; model arg optional; `--model-of`. |
| 5 | Every mandate contained *"never name any endpoint path… in this mandate"* inside the agent's own prompt (can be misread as "never write paths in a handoff"). No credential rule although tool calls are exported publicly. | Meta line removed (enforced by `src/lint_mandates.py` instead); generic no-credentials rule; Foreman numbers requirements (REQ-n), Inspector's verdict maps IDs to evidence. |
| 6 | Submission repo had mandates but **none of the tooling FACTORY.md tells judges to run**. | `package-submission.sh` → `factory/` + synced `mandates/`; `run_seat.py`/scripts work in both layouts. |
| 7 | `preflight.sh` could not catch: leftover `TBD`, a real key inside `room.json`/history, non-public repo, gaps in stage folders, bad `room.json`. | `--final` mode + those checks (4 fixture scenarios incl. a secret only in history). |
| 8 | Result `.gitignore` ignored `dist/` and `build/` → builds locally, fails from a fresh clone. | No longer ignored. |
| 9 | RUNBOOK 3b re-committed files `bootstrap-repo.sh` already committed (`git commit` exits 1). | Step removed. |
| 10 | `.env.example` referenced but missing; FACTORY.md template had placeholder clone URLs and no measured-evidence sections. | Added; template rewritten (stand-up from the repo itself, safeguards, run facts, "bad work caught"). |
| 11 | New: `src/analyze_room.py` (human-message count, reciprocity, rejections, stage timings, commit authors). | **Heuristic**: I don't know BAND's export schema. If it prints "No message-like records", paste 30 lines of `room.json`. |

**Not testable here (no BAND/Featherless/Docker/harness):** a real seat run, the `agent_config.yaml`
schema (the template tells you to paste your redacted file), `/global/health`, the real `room.json`.
Treat Gate A/B below as the real test.

## 2. Three decisions only you can make

1. **Reviewer independence.** All four seats are the same Flash model; same-model review shares blind
   spots, and *"review changed something"* is a stated teamwork criterion. Pick one different family for
   Inspector (list with the `curl … /v1/models` command in RUNBOOK Phase 1b), add it to `opencode.json`,
   set `Model:` in `mandates/inspector.md`. Cheapest high-value change; ~10 min. Don't change Smith's.
2. **Scope vs. time.** A complete stage 1 is the minimum for eligibility; each further stage adds
   "how far it got". Other entries report 2.5 h to 12 h for all four stages. With a Flash model assume the
   slow end. Use `--stages 2` if you will start later than T−9h (rule below).
3. **Hands-off discipline.** Autonomy is scored on *"the dispatch is the only human input — no steering,
   approvals or reruns"*. If the factory stalls, you do not nudge it in the room. You stop it and submit
   what is complete.

## 3. Schedule

### Gate A — ready (≤ 45 min)
```sh
uv sync && chmod +x *.sh
cp .env.example .env && chmod 600 .env          # FEATHERLESS_API_KEY, RESULT_REPO
python3 src/lint_mandates.py                    # must print 0 violations
```
`opencode.json` lists every model used; `agent_config.yaml` has all four seats.

### Gate B — rehearsal (≤ 60 min)
1. RUNBOOK Phase 1b: start all four seats, scratch-room ping, watch `logs/*.log` for 429/timeouts.
2. Toy **stage 1 only**: `./render-dispatch.sh toy --stages 1` → Foreman. Then download `room.json`,
   `python -m harness check <toy-result> --track toy`, `python src/analyze_room.py room.json`.
   Pass = reciprocal handoffs visible, harness gates green, analyzer recognises the export.
   (Skip the full 4-stage toy loop. It costs hours and credits you need for the real run.)

### Gate C — the graded run
- **Latest start: T−9h for 4 stages, T−6h for `--stages 2`.** Later than that → `--stages 1`.
- Fresh room, fresh repo: `bootstrap-repo.sh …/result-final`, `RESULT_REPO=… ./start-factory.sh`
  (it must print "All 4 seats are up"), start **OBS**, then `./render-dispatch.sh pocketful` → paste to Foreman.
- Then hands off. Allowed: watching logs and the room, restarting a dead process (the watchdog does).
  Not allowed: any message in the room, any file edit in the result repo.
- **Hard stop at T−3h** whatever state it is in: `./stop-factory.sh`, stop OBS.
  Incomplete `stage-K/` → `git rm -r stage-K`, commit as `factory-bootstrap`, disclose in FACTORY.md.

### Gate D — packaging (reserve ≥ 3 h)
```sh
# in BAND Desktop: room ⋮ → Open in Band console → download FULL session → result-final/room.json
./package-submission.sh "$RESULT_REPO"
python src/analyze_room.py "$RESULT_REPO/room.json" --repo "$RESULT_REPO"   # → FACTORY.md numbers
$EDITOR "$RESULT_REPO/FACTORY.md"       # fill every TBD (stage table, run facts, 2 real "bad work caught")
./preflight.sh "$RESULT_REPO" --final   # must end PASSED
git -C "$RESULT_REPO" push origin main  # then open the repo URL in a private window
```
If a real key shows up in `room.json`: rotate the key first, then replace with `[REDACTED]` and **say so**
in FACTORY.md. Do not fix product code after the run.

## 4. If it goes wrong

| Symptom | Do |
|---|---|
| `start-factory.sh` exits "seat X died during startup" | Read `logs/X.log` (model not in `opencode.json`, bad key, 429). Fix, restart. Nothing is lost; no dispatch sent yet. |
| Seat repeatedly restarting / `GAVE-UP` in `events.log` | Provider limits or a bad model id. Stop, fix, **start a fresh room and repo** (a mid-run restart of the run is a "rerun"). |
| Foreman silent > 30 min, no tool activity | Stalled. Do not nudge. Stop at the T−3h rule; submit completed stages. |
| Stage N accepted but fails the isolated harness | Submit stages < N only (preflight shows which); disclose. |
| Credits nearly out | Check Featherless usage after stage 1; if projected spend > remaining, stop after the current stage. |
| Analyzer recognises nothing | Paste 30 lines of `room.json`; numbers can also be read by hand from the console. |

## 5. Video (≤ 4 min; check the form's limit). Missing room recording = disqualified

**Capture:** OBS, canvas 1280×720, **5 fps**, x264 CRF 28, `.mkv`, started at dispatch (~0.5 GB/h).
Time-lapse the 4–6 h: `ffmpeg -i room.mkv -an -vf "setpts=PTS/120,fps=30" -c:v libx264 -crf 26 room-120x.mp4`.

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Title; `mandates/` listing | "Four generic seats; swap the task, keep the mandates." Show `lint_mandates` passing. |
| 0:20–1:10 | Time-lapse of the room, then **real-speed** Foreman→Smith and Smith→Inspector handoffs with @handles both directions | The single human message; REQ IDs in the handoff. |
| 1:10–2:00 | A real **rejection** by Inspector with its command and output, the fix revision, re-accept | "Bad work caught": the evidence, not the claim. |
| 2:00–2:50 | Fresh clone → `harness run --stage N --mode isolated` → `claimed stage: N`; the UI in a browser at phone width and desktop | Result + App criterion. |
| 2:50–3:30 | `FACTORY.md`: seats, safeguards, measured time/cost, limits | Stand-up instructions + honest limitations. |
| 3:30–4:00 | `analyze_room` output: human messages = dispatches, commits all by seats | Autonomy + traceability. |

## 6. Deck (≤ 7 slides; build after the run; needs real numbers)
1. **Title + claim:** "A generic four-seat band: one dispatch, no human steering." Repo URL, track.
2. **The band:** seats, models, handoff diagram (Foreman → Smith → Inspector → Stresser → Foreman).
3. **Generic by construction:** the portability test; lint output; what lives in the dispatch vs. in a mandate.
4. **Catching bad work:** independent re-run, REQ-ID verdicts, Stresser probes, **two real incidents** from the room.
5. **Result:** stage reached, harness counts, isolated-mode run, wall-clock and spend per stage.
6. **Teamwork evidence:** human messages = N, reciprocal pairs, commits by author, room↔code trace.
7. **Limits + stand-up:** same-provider risk, secrets-in-room mitigation, pointer to `FACTORY.md`.

Send me `analyze_room` output + `FACTORY.md` numbers + the harness result and I'll build the `.pptx` in one pass.

## 7. Form copy (fill brackets after the run)

- **Title:** `[Name]: a four-seat dark factory that proves its own work`
- **Short:** Four generic BAND seats (planner, builder, independent reviewer, adversarial tester) built pocketful through stage [N] from one dispatch. [X/Y] harness checks pass in isolated mode. Mandates are task-agnostic and lint-enforced.
- **Long:** the 4 headings: *The band* · *Why the mandates are generic* · *How it catches and recovers from bad work (2 real incidents)* · *Measured result, cost and limitations*; link `FACTORY.md`.
- **Tags:** Band Agentic Mesh, Featherless, OpenCode (plus whatever the tag picker offers closest).

## 8. Submission checklist (disqualifiers first)
- [ ] No mandate names track detail → `lint_mandates.py` 0 violations; `preflight --final` clean
- [ ] Video contains the BAND room recording **and** a walkthrough
- [ ] `stage-1/` (≥) builds and serves from a clean container with no network → isolated harness run
- [ ] Public GitHub repo opens in a private window; contains `stage-N/`, `mandates/`, `FACTORY.md`, `room.json`
- [ ] `FACTORY.md` has no `TBD`; includes measured time and cost, and how bad work is caught
- [ ] Every commit in `stage-*` authored by a seat (`analyze_room --repo`), human messages = dispatch count
- [ ] Cover image, slides, video uploaded; confirmation receipt saved
