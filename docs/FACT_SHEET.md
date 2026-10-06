# FACT_SHEET.md — Pocketful Dark Factory: Verified Ground Truth

> Every claim in this file is traced to a `room.json` message id / timestamp,
> a file read, or a command run. If a claim cannot be verified, it says "unverified".
> This file is the single source of truth for all other docs.

---

## 1. Room Overview

| Fact | Value | Source |
|---|---|---|
| Room id | `48bd09b2-3c1e-426c-9beb-29d79b6f8d91` | `room.json`.room.id |
| Room title | "Oct 5, 2026, 9:14:51 AM" | `room.json`.room.title |
| Total messages | **683** | `len(messages)` parsed |
| First message timestamp | `2026-10-05T09:15:24.714Z` | `messages[0].insertedAt` |
| Last message timestamp | `2026-10-05T12:33:04.909Z` | `messages[-1].insertedAt` |
| Room duration | **3 h 17 m 40 s** | last minus first |
| Room exported at | `2026-10-05T12:54:48.332Z` | `room.json`.exportedAt |

## 2. Messages by Sender

| Sender | Count | Source |
|---|---|---|
| Smith | 249 | parsed |
| Inspector | 257 | parsed |
| Foreman | 95 | parsed |
| Stresser | 78 | parsed |
| Metal (human) | **4** | parsed |

## 3. Human Messages (complete list)

| # | id | Timestamp (UTC) | Content summary |
|---|---|---|---|
| 1 | `9cd51be9-4edb-4cbd-96a1-aeff05772ef5` | `2026-10-05T09:15:48.169Z` | **Initial dispatch** — full Stage 1-4 work order to @Foreman |
| 2 | `7f0a3bf3-6096-42d0-abc6-deb9df8387f7` | `2026-10-05T09:34:36.216Z` | **Identical re-dispatch** — same full text, sent again to @Foreman (Foreman timed out at 09:33) |
| 3 | `876fffed-2afb-48e2-bfe2-e80a2caf0544` | `2026-10-05T12:11:42.035Z` | **"continue"** — one-word resumption after ~1h55m stall |
| 4 | `6beca9bc-f98e-4de7-bc57-fd60d9ecf3e7` | `2026-10-05T12:18:01.948Z` | **Steering note** to @Stresser @Inspector @Smith: "Next: commit to review to probe to Stage 2 report, then Stage 3 opens." |

Autonomy note: The hackathon rubric states "the task you dispatch for each stage is the only human input."
Messages 2-4 are not task dispatches. Message 2 is a re-send caused by a timeout; messages 3-4 are
reactive steering during a stall. These will cost points in the autonomy criterion and must be disclosed.

## 4. OpenCode Timeout Events

| # | id | Timestamp (UTC) | Sender | Type |
|---|---|---|---|---|
| 1 | `1908eeac-7ed2-4d1a-a5d7-aa66e8d1728b` | `2026-10-05T09:33:22.587Z` | Smith | error |
| 2 | `76733bc9-364e-4ae8-a5f5-4094ba23928f` | `2026-10-05T10:16:31.991Z` | Smith | error |
| 3 | `19474929-093d-441d-9bbd-cb719f5b730f` | `2026-10-05T12:33:04.909Z` | Smith | error (last message) |

All three contain text "OpenCode timed out before completing the turn."

Factory FATAL in `events.log`: `2026-10-05T12:39:09Z FATAL opencode server died (see logs/opencode.log)`
Source: `factory/run-evidence/events.log` (read directly; 72 bytes, 1 line).

Stall: Timeout 2 at `10:16:31Z` to human "continue" at `12:11:42Z` = **~1 h 55 m stall**.

## 5. Stage 1 Timeline

| Event | Timestamp (UTC) | Message id | Notes |
|---|---|---|---|
| Human dispatch | `09:15:48Z` | `9cd51be9` | |
| Smith timeout 1 / re-dispatch | `09:33:22Z` / `09:34:36Z` | `1908eeac` / `7f0a3bf3` | Human resent identical dispatch |
| Smith committed `ef1a437` | `09:40:41Z` | `f52c30d5` | 147/147 harness + 145/145 smoke |
| Foreman issued review order | `09:41:25Z` | `6f2ea3d9` | to Inspector |
| Inspector ACCEPTED `ef1a437` (1st) | `09:44:52Z` | `e5630170` | 147/147 + 145/145 |
| Inspector ACCEPTED `ef1a437` (2nd) | `09:49:34Z` | `fa720687` | REQ table all verified |
| Foreman issued hardening order | `09:45:19Z` | `e82de0aa` | to Stresser |
| Stresser CLEAN + C1 concern | `09:51:47Z` | `76888d2f` | "1 unresolved concern (cosmetic, low)" |
| Foreman escalated C1 to Smith | `09:52:12Z` | `582bedd8` | "FOLLOW-UP FIX" work order |
| Smith fixed C1 + C2 bonus | `09:57:03Z` | `d3b53a55` | Committed `5620886` |
| Inspector delta-ACCEPTED `5620886` (1st) | `09:59:41Z` | `b054d56f` | |
| Inspector delta-ACCEPTED `5620886` (2nd) | `10:02:19Z` | `efd0a80a` | |
| Foreman Stage 1 FINAL REPORT | `10:00:00Z` | `2c37bc65` | to @Metal |
| **Stage 1 duration** | **~44 min** | 09:15:48 to 10:00:00 | dispatch to final report |

## 6. Defect Discovery

### C1: 0-byte request bodies returned 422 instead of 400

| Item | Value | Source |
|---|---|---|
| Found by | **Stresser** | msg `76888d2f` at `09:51:47Z`: "1 unresolved concern (cosmetic, low severity)" |
| Classification at discovery | "not counted as a defect; behaviour arguably within spec" | msg `76888d2f` |
| Escalated by | Foreman | msg `582bedd8` at `09:52:12Z` |
| Fixed by | Smith | msg `d3b53a55` at `09:57:03Z`, commit `5620886` |
| Inspector action on `ef1a437` | **ACCEPTED** (not rejected) at 09:44 and 09:49 | msgs `e5630170`, `fa720687` |
| Inspector action on `5620886` | Delta-ACCEPTED at 09:59 and 10:02 | msgs `b054d56f`, `efd0a80a` |

KEY FACT: Inspector NEVER rejected `ef1a437`. C1 was found by Stresser after Inspector's acceptance.
Any document stating "Inspector rejected ef1a437" is false.

### C2 (Bonus): Cold-start index failure before first POST /_test/reset

| Item | Value | Source |
|---|---|---|
| Found by | **Smith** (self-found) | msg `d3b53a55` at `09:57:03Z`: "Bonus defect found & fixed while verifying C1: on a fresh container, Store.__init__ built the initial..." |
| Escalated by | N/A - Smith found and fixed autonomously | |
| Fixed in | `5620886` (same commit as C1 fix) | msg `d3b53a55` |
| Inspector action | Delta-verified fix in `5620886` review | msgs `b054d56f`, `efd0a80a` |

KEY FACT: C2 was a bonus self-find by Smith, not found by Inspector or Stresser.

## 7. Test Results

| Suite | Count | Who ran | Revision | Source |
|---|---|---|---|---|
| Official harness (Smith, 1st run) | 147/147 PASS | Smith | `ef1a437` | msg `f52c30d5` at `09:40:41Z` |
| Private smoke suite (Smith) | 145/145 PASS | Smith | `ef1a437` | msg `f52c30d5` |
| Official harness (Inspector, independent) | 147/147 PASS | Inspector | `ef1a437` | msg `e5630170` at `09:44:52Z` |
| Private smoke suite (Inspector) | 145/145 PASS | Inspector | `ef1a437` | msg `e5630170` |
| Official harness (Inspector, post-C1-fix) | 147/147 PASS | Inspector | `5620886` | msg `b054d56f` at `09:59:41Z` |
| Private smoke suite (Inspector, post-fix) | 145/145 PASS | Inspector | `5620886` | msg `b054d56f` |
| Stresser: 50-way concurrency | 2,520 requests, ~565 rps, 0 5xx, 100 MiB peak | Stresser | `ef1a437` | msg `76888d2f` at `09:51:47Z` |
| Stresser: export/destroy/import | PASS | Stresser | `ef1a437` | msg `76888d2f` |

Harness sub-suite breakdown (24+39+51+19+14): cited in master prompt but NOT directly
shown in room.json messages. The 147 total is confirmed by multiple independent runs.
Do not state the sub-group breakdown as verified fact.

## 8. Seat Models

| Seat | Model | Source |
|---|---|---|
| Foreman | `zai-org/GLM-5.3-Flash` | `mandates/foreman.md` line 2 |
| Smith | `zai-org/GLM-5.3-Flash` | `mandates/smith.md` line 2 |
| Inspector | **`MiniMaxAI/MiniMax-M2.5`** | `mandates/inspector.md` line 2 |
| Stresser | `zai-org/GLM-5.3-Flash` | `mandates/stresser.md` line 2 |

`factory/run-evidence/seat_models.txt` -- FILE DOES NOT EXIST (missing from run-evidence).
`factory/run-evidence/started_at` -- FILE DOES NOT EXIST (missing from run-evidence).

## 9. Stage 2 Status

Foreman dispatched Stage 2 work order at `10:01:30Z` (msg `77df6920`).
Smith was actively implementing Stage 2 in `stage-2/main.py` at room export time.
Last Smith message: harness run command was aborted ("User aborted the command",
msg `380b6680` at `12:33:04Z`), then Smith timed out (msg `19474929`).

Foreman status at `12:12:22Z` (msg `232034a0`): "Stage 2 is actively in progress:
Smith has created stage-2/ (copy-forward done, code being extended per the 26-requirement
work order, local testing underway; not yet committed)."

CONCLUSION: Stage 2 was never committed to the result repo. It existed only in
Smith's working tree. Stage 2 is not part of the submission.

## 10. Official Hackathon Rules (Key Constraints)

| Item | Rule |
|---|---|
| Video length | No explicit limit stated |
| Video content | Must include BAND Desktop room recording + walkthrough. No room recording = disqualified. |
| Slide presentation | Required field in submission form |
| Repository | One public GitHub repository |
| Minimum eligibility | Complete Stage 1 |
| Autonomy criterion | "the task you dispatch for each stage is the only human input" |
| Submission deadline | Oct 6, 2:59 AM Eastern = 2026-10-06T06:59:00Z |

## 11. Missing Files

| File | Status | Impact |
|---|---|---|
| `submission-assets/video/video-script.md` | EXISTS (2026-10-06) | Earlier path `submission-drafts/video-script.md` was empty; the script lives under `submission-assets/video/` |
| `factory/run-evidence/seat_models.txt` | DOES NOT EXIST | Do not invent it. Models are `mandates/*.md` `Model:` lines; see `factory/run-evidence/README.md` |
| `factory/run-evidence/started_at` | DOES NOT EXIST | Do not invent it. Start time is dispatch `9cd51be9` at `09:15:48Z` |
| Slide deck | EXISTS | `submission-assets/slides/pocketful-factory.pdf` |
| `SUBMISSION_CHECKLIST.md` | EXISTS (2026-10-06) | Root checklist; earlier line-number cites referred to a draft that was not in tree |

## 12. Claim Audit Table (historical; line numbers as of the first audit)

The table below records false claims found in an earlier tree. Several were
corrected before this file's 2026-10-06 refresh. Treat §1–§10 and §13 as
current; do not copy a FALSE row into the form if the live file no longer
says that.

| Doc:line | Claim | Status | Evidence |
|---|---|---|---|
| `README.md:10` | "without any human steering after the initial dispatch" | FALSE | 4 human messages (section 3) |
| `README.md:58-59` | POST /_test/reset with fixture body returns {"status":"ok"} | FALSE | spec + msg `9fabe1d1`: returns 204 No Content |
| `FACTORY.md:41` | Inspector model: zai-org/GLM-5.3-Flash | FALSE | mandates/inspector.md line 2: MiniMaxAI/MiniMax-M2.5 |
| `FACTORY.md:251-253` | Stage 1 ~07:30 to ~10:15 UTC, ~2h45m | FALSE | Dispatch 09:15:48Z, final report 10:00:00Z (~44 min) |
| `FACTORY.md:262` | Human messages: 1 | FALSE | 4 human messages |
| `FACTORY.md:263` | Total room messages: [unfilled] | UNFILLED | Value is 683 |
| `FACTORY.md:265` | Rejections by Inspector that changed the code: 1 | FALSE | Inspector never rejected; Stresser raised concern |
| `FACTORY.md:272` | Incident 1 header: "Revision ef1a437 rejected" | FALSE | Inspector ACCEPTED ef1a437 (msgs e5630170, fa720687) |
| `FACTORY.md:278` | Incident 2 header: "ef1a437 rejected during verification" | FALSE | C2 self-found by Smith, not a rejection event |
| `FACTORY.md:274` | "Evidence Produced: Inspector repro curls" | MISLEADING | C1 was Stresser's probe, not Inspector's |
| `FACTORY.md:280` | "Inspector fresh-container test...failed with HTTP 400" | FALSE | Smith found C2 as bonus; Inspector did not run this test |
| `FACTORY.md:285` | cat ~/band-work/factory/logs/started_at | UNRUNNABLE | started_at file does not exist |
| `SUBMISSION_CHECKLIST.md:28` | "HUMAN-TODO: operator must place room.json" | OUTDATED | band-room-export/room.json already present |
| `SUBMISSION_CHECKLIST.md:73` | Video script: PASS | FALSE | File does not exist |
| `form.md:33` | "Autonomy: Exactly 1 human message (the initial dispatch)" | FALSE | 4 human messages |
| `form.md:13` | Inspector model: MiniMaxAI/MiniMax-M2.5 | TRUE | Matches mandate |

## 13. Current submission files (2026-10-06)

Live files that judges will read, checked against §§1–10:

| File | Honest disclosure present |
|---|---|
| `README.md` | Four human messages; Stage 1 only; 204 No Content on reset |
| `FACTORY.md` | Inspector `MiniMaxAI/MiniMax-M2.5`; Stage 1 ~44 min; 4 human messages; 683 room messages; Inspector rejections that changed code = 0; C1 Stresser; C2 Smith; FATAL `12:39:09Z`; spend unverified |
| `submission-assets/submission-drafts/form.md` | Four human messages; no Inspector-rejection origin for C1/C2 |
| `SUBMISSION_CHECKLIST.md` | Same ledger; operator still must push public GitHub |
| `factory/templates/*` | Templates no longer claim single-dispatch autonomy or a Flash Inspector |

Still true and not to be reversed:

- 4 human messages, 3 OpenCode timeouts, ~1h55m stall, FATAL at `12:39:09Z`
- Stage 1 only (147/147 harness, 145/145 smoke)
- Inspector NEVER rejected `ef1a437`
- C1 raised by Stresser; C2 self-found by Smith

