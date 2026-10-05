# Hackathon Submission Checklist & Verification Report

Status Legend:
- **PASS**: Verified with real command execution and actual output.
- **FAIL / BLOCKER**: Requirement not yet met; must be resolved before submission.
- **HUMAN-TODO**: Requires operator action (BAND Desktop room export, GitHub push, form submission).

---

## 1. Inventory & Stage Eligibility

| Requirement | Status | Evidence / Notes |
|---|---|---|
| Complete Stage 1 | **PASS** | `stage-1/` committed at `5620886`. Complete and buildable from own folder. Passes 147/147 isolated harness checks. |
| Stage 2 .. 4 Completeness | **NOT SHIPPED** | Stage 2 in-progress draft preserved on branch `draft-stage-2` (`d473dfa`). Stages 3 & 4 not reached. Per hackathon rules, only completed stages ship. |
| No incomplete / partial stages on main | **PASS** | `stage-2/` removed from `main` branch. Only `stage-1/` ships on `main`. |

---

## 2. Repository Structure

| File / Folder | Status | Evidence |
|---|---|---|
| `/README.md` | **PASS** | Present at repo root with clone, build, run, and stage status table. |
| `/FACTORY.md` | **PASS** | Present with seat specifications, model configurations, process safeguards, and bad-work recovery log. |
| `/mandates/` | **PASS** | 4 distinct seat mandates (`foreman.md`, `smith.md`, `inspector.md`, `stresser.md`). |
| `/task/` | **PASS** | Present at `task/dispatch.md` containing the unredacted task specification and invariants. |
| `/band-room-export/` | **HUMAN-TODO** | Folder created; operator must place `room.json` exported from BAND Desktop (menu -> Open in Band -> Download full session). |
| `/stage-1/` | **PASS** | Complete service: `Dockerfile`, `main.py`, `RUN.md`. Zero external runtime dependencies. |

---

## 3. Mandate Neutrality (Disqualification Gate)

| Check | Status | Evidence / Command Output |
|---|---|---|
| Zero track-specific endpoints/routes | **PASS** | `python3 src/lint_mandates.py`: `lint_mandates: 4 mandates, 0 violation(s)` |
| Domain denylist scan (110 terms) | **PASS** | Denylist scan of all 4 mandates against extracted pocketful spec terms yielded **0 hits**. |
| Distinct seat roles | **PASS** | 4 seats: Coordinator (Foreman), Builder (Smith), Reviewer (Inspector), Tester (Stresser). |
| Reviewer independence | **PASS** | Inspector uses `MiniMaxAI/MiniMax-M2.5`, distinct from GLM-5.3-Flash builder. |

---

## 4. Container & Offline Network Compliance

| Requirement | Status | Evidence |
|---|---|---|
| CPU cap: 2 vCPUs | **PASS** | Verified via `docker run --cpus=2 --memory=2048m -p 8080:8080`. Container started instantly. |
| Memory cap: 2048 MB | **PASS** | Verified under isolated container test (`--memory=2048m`). Peak memory << 100 MB. |
| No runtime outbound calls | **PASS** | Verified in isolated mode: `--network none`. Standard library only (`http.server`). 147/147 checks pass. |
| Port 8080 / GET `/health` | **PASS** | `curl -i http://127.0.0.1:8080/health` -> HTTP 200 `{"status": "ok"}`. |
| Strict request contracts | **PASS** | `POST /_test/reset` (0-byte) -> 400 `malformed_request`. `{}` -> 422 `validation_failed`. |

---

## 5. Security & Hygiene

| Check | Status | Evidence |
|---|---|---|
| Working tree secret scan | **PASS** | Zero API keys or tokens in files (`.env` & `agent_config.yaml` gitignored). |
| Git history secret scan | **PASS** | `git log -p` scan found zero live secret credentials in commit history (5 commits checked). |
| No submodules or symlinks | **PASS** | `git submodule status` = None; symlinks in repo = None. |
| Clean clone test | **PASS** | `git clone` from local git repo succeeds cleanly in temporary directory (`revision 0f5d7ee`). |

---

## 6. Video & Form Pack

| Deliverable | Status | Location / Instructions |
|---|---|---|
| Screen recording (`room.mkv`) | **PASS** | Full 5h15m recording saved to `/home/sp3ct0r/band-work/room.mkv` (155 MB). |
| Edited timelapse video (<= 4 min) | **PASS** | Rendered to `result-final/room-timelapse.mp4` (2m37s, 7.9 MB, 120x speedup). |
| Video walkthrough script | **PASS** | Documented in `submission-drafts/video-script.md` with required room screen recording. |
| Submission form text | **PASS** | Prepared in `submission-drafts/form.md` (short description: 172 chars, < 200 max). |
