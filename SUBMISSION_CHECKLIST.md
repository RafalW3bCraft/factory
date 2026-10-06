# Submission checklist

Ground truth: [`docs/FACT_SHEET.md`](docs/FACT_SHEET.md).
Do not claim more than that file can source.

## Required form fields

| Item | Status | Location |
|---|---|---|
| Public GitHub repository | Operator must push (this checkout is local-only) | remote `origin` |
| Slide presentation | Present | `submission-assets/slides/pocketful-factory.pdf` |
| Video (BAND room + walkthrough) | Present; uses cropped room excerpts | `submission-assets/video/pocketful-factory-video.mp4` |
| Form copy | Present | `submission-assets/submission-drafts/form.md` |
| `room.json` | Present | `room.json` (683 messages) |

## Eligibility and honesty

| Item | Status | Evidence |
|---|---|---|
| Stage 1 complete | Yes | 147/147 harness, 145/145 smoke; `docs/FACT_SHEET.md` §5–§7 |
| Stages 2–4 | Not shipped | Stage 2 uncommitted at export; 3–4 not reached |
| Human messages | **4**, not 1 | dispatch, identical re-dispatch, `continue`, steering note |
| OpenCode timeouts | **3** | 09:33, 10:16, 12:33 UTC |
| Stall | **~1h55m** | timeout 2 → `continue` |
| FATAL | `2026-10-05T12:39:09Z` | `factory/run-evidence/events.log` |
| Inspector vs `ef1a437` | **ACCEPTED**, never rejected | msgs `e5630170`, `fa720687` |
| C1 | Raised by **Stresser** | msg `76888d2f`; fixed in `5620886` |
| C2 | Self-found by **Smith** | msg `d3b53a55`; same commit |

## Operator actions still required

- Push this branch to a **public** GitHub repository (do not use `--force` on `main`/`master`).
- Paste the form copy into the hackathon form; keep the four-message autonomy disclosure.
- Confirm the video file is attached in the form (git LFS is not used; the mp4 is in-tree).
- Featherless spend figure: unverified; leave blank or mark unverified.

## Do not

- Re-run `start-factory.sh` or `run_seat.py` against the live room (breaks autonomy, burns credits).
- Edit `stage-1/**`, `mandates/**`, `factory/factory/mandates/**`, or `room.json`.
- Claim Inspector rejected `ef1a437`.
