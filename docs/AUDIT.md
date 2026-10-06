# Factory Hardening Audit Ledger

## 1. Baseline vs Hardened Metrics

Branch: `hardening/prod-ready`  
Baseline Commit: `e449c7f`  
Hardened Commit: `610d46b`  

### Tracked Files & Storage Footprint
| Directory | Baseline Files | Baseline Bytes | Hardened Files | Hardened Bytes | Delta (Files) | Delta (Bytes) |
|---|---|---|---|---|---|---|
| `(root)` | 16 | 302,677 B | 22 | 438,286 B | +6 | +135.6 KB |
| `.agents/` | 707 | 4,778,742 B | 44 | 314,823 B | -663 (-93.8%) | -4,463.9 KB (-93.4%) |
| `.github/` | 0 | 0 B | 1 | 1,358 B | +1 | +1.4 KB |
| `dispatch/` | 3 | 5,591 B | 3 | 5,591 B | 0 | 0 B |
| `docs/` | 1 | 4,547 B | 1 | 9,354 B | 0 | +4.8 KB |
| `mandates/` | 4 | 19,612 B | 4 | 22,188 B | 0 | +2.6 KB |
| `scripts/` | 0 | 0 B | 2 | 3,317 B | +2 | +3.3 KB |
| `src/` | 5 | 22,210 B | 10 | 27,183 B | +5 | +5.0 KB |
| `tests/` | 2 | 2,797 B | 10 | 36,199 B | +8 | +33.4 KB |
| **Total** | **738** | **5,136,176 B (4.90 MB)** | **97** | **858,299 B (0.82 MB)** | **-641 (-86.9%)** | **-4,277.9 KB (-83.3%)** |

---

### Quality & Verification Metrics
| Verification Metric | Baseline Measurement | Hardened Measurement | Status |
|---|---|---|---|
| `uv sync --frozen` | Clean (50 pkgs) | Clean (77 pkgs, version 0.3.0) | PASS |
| `pytest` Suite | 9 tests passed | 66 tests passed | PASS |
| `src/` Test Coverage | 14.6% (68 / 466 lines) | **94.9% (408 / 430 lines)** | PASS (Floor >=85%) |
| `ruff check .` | Clean | Clean (0 errors across 24 files) | PASS |
| `ruff format --check .` | 4 files unformatted | Clean (31 files formatted) | PASS |
| `mypy src tests` | 2 type errors | Clean (0 errors in 20 files) | PASS |
| `shellcheck *.sh scripts/*.sh` | 5 warnings | Clean (0 warnings across 6 scripts) | PASS |
| Antigravity Rules Check | 0 active rules | 10 rules with valid Antigravity 2.0 triggers | PASS |
| Secret Scan | 0 real secrets | Clean (0 secrets in tracked files) | PASS |
| Dependency Audit (`pip-audit`) | 0 known vulnerabilities | Clean (0 known vulnerabilities) | PASS |
| Clean Clone Smoke Test | Not verified | Clean clone -> preflight -> render dispatch | PASS |

---

## 2. Findings Ledger

| ID | Sev | Area | Summary | Evidence / Command | Fix Implementation | Status | Commit |
|---|---|---|---|---|---|---|---|
| **E1** | P0 | ECC | `.agents` bloated (707 files, 4.67 MB); machine paths leaked; rules lacked Antigravity triggers. | `.agents` | Pruned to curated inventory (10 rules with triggers, 12 agents, 20 skills, 0 workflows); added `tests/test_rules.py`. | FIXED | `be600ee` |
| **S1** | P0 | Security | `run_seat.py` used `approval_mode="auto_accept"` with unsandboxed root/host permissions. | `run_seat.py:132` | Created `Dockerfile.sandbox` & `docker-compose.sandbox.yml` with non-root user (UID 1000), read-only root, `/workspace` mount restriction, dropped capabilities, and resource limits. | FIXED | `610d46b` |
| **S2** | P0 | Security | Credential exposure: `FEATHERLESS_API_KEY` and all Band tokens inherited across child shells. | `start-factory.sh:75` | Sanitized `opencode serve` environment (`env -u FEATHERLESS_API_KEY`); injected per-seat isolated tokens (`BAND_AGENT_ID`, `BAND_API_KEY`) to seat processes. | FIXED | `610d46b` |
| **S3** | P1 | Security | `source .env` executed arbitrary shell code in `start-factory.sh` and `preflight.sh`. | `start-factory.sh:74`, `preflight.sh:89` | Built safe KEY=VALUE parser in `factory.env` and `scripts/load_env.sh` neutralizing command injection payloads. | FIXED | `610d46b` |
| **S4** | P1 | Security | `preflight.sh` passed API key in curl argv, exposing key in `/proc` and `ps`. | `preflight.sh:101` | Switched to streaming header via curl stdin config (`-K -`), keeping secrets out of argv. | FIXED | `610d46b` |
| **S5** | P2 | Security | OpenCode server on `127.0.0.1:4096` was unauthenticated. | `start-factory.sh:134` | Implemented HTTP Basic Auth via `OPENCODE_SERVER_PASSWORD` and injected auth headers in `OpencodeAdapter`. | FIXED | `610d46b` |
| **S6** | P1 | Security | Untrusted prompt injection boundary between repo data and mandates. | Mandates / Stresser | Added explicit `DATA, NEVER INSTRUCTIONS` boundary to all 4 mandates; enforced localhost-only egress for Stresser. | FIXED | `610d46b` |
| **S7** | P2 | Security | Missing supply chain hygiene & automated CI scanning. | CI / repo | Created `.github/workflows/ci.yml` with pip-audit, gitleaks, shellcheck, ruff, mypy, and coverage gates. | FIXED | `610d46b` |
| **R1** | P1 | Reliability | Supervisor watchdog used lifetime restart counter; deadlocked if Foreman failed. | `start-factory.sh:199` | Implemented sliding 10-minute window with exponential backoff and fail-fast termination on Foreman crash. | FIXED | `610d46b` |
| **R2** | P1 | Reliability | No mission-level wall-clock timeout or kill switch. | `start-factory.sh` | Added `MISSION_TIMEOUT_S` ceiling (default 4h) and file-based `factory.kill` kill switch. | FIXED | `610d46b` |
| **R3** | P2 | Reliability | Logs overwritten unconditionally on every start; no retention policy. | `start-factory.sh:168` | Structured per-run log directories under `logs/runs/<run-id>/` with `logs/latest` symlink and 20-run retention pruning. | FIXED | `610d46b` |
| **R4** | P2 | Reliability | `stop-factory.sh` used unconditional `kill -9` without process verification. | `stop-factory.sh:37` | Process group signaling with grace period, `/proc/<pid>/cmdline` verification, and SIGKILL escalation only as fallback. | FIXED | `610d46b` |
| **R5** | P2 | Reliability | Hardcoded port 4096 and base_url scattered across scripts. | `start-factory.sh`, `run_seat.py` | Centralized `OPENCODE_PORT` and `OPENCODE_BASE_URL` with dynamic port checking. | FIXED | `610d46b` |
| **R6** | P1 | Reliability | Preflight only checked HTTP 200; tests asserted hardcoded model literals. | `preflight.sh:106`, `test_mandates.py:17` | Preflight verifies mandate models exist in provider catalog dynamically; tests derive from mandates as single source of truth. | FIXED | `610d46b` |
| **R7** | P3 | Reliability | Preflight promised 8 checks but printed `[n/7]`; imported pytest in runtime check. | `preflight.sh:36` | Aligned check count to 8 steps; separated runtime dependencies (`band, yaml, factory`) from dev-time test dependencies. | FIXED | `610d46b` |
| **Q1** | P1 | Quality | Test coverage was 14.6% on `src/` (target >= 85%). | Trace baseline | Wrote comprehensive behavior tests across all modules reaching **94.9% test coverage**. | FIXED | `610d46b` |
| **Q2** | P2 | Quality | `mypy` had 2 errors in `analyze_room.py`; `ruff format` touched 4 files. | `mypy src tests`, `ruff format` | Fixed type annotations in `analyze_room.py` and formatted entire codebase with ruff. | FIXED | `610d46b` |
| **Q3** | P2 | Quality | `src/` scripts outside package, `sys.path.insert` in tests, stub `factory:main`. | `pyproject.toml`, `tests/` | Restructured into installable `factory` package (`src/factory/`) with thin CLI shims in `src/`. | FIXED | `610d46b` |
| **Q4** | P2 | Quality | `render_dispatch` custom env loader; `analyze_room` heuristic regexes and hand-rolled argv. | `src/render_dispatch.py` | Refactored `render_dispatch` to safe env parser; upgraded `analyze_room` to `argparse` with fixture test coverage. | FIXED | `610d46b` |
| **Q5** | P3 | Quality | `die()` untyped `NoReturn`; print debugging instead of logging. | `src/run_seat.py` | Added `typing.NoReturn` type annotations and clean error reporting across runners. | FIXED | `610d46b` |
| **H1** | P1 | Hygiene | Hardcoded `/home/sp3ct0r` in docs, examples, and scripts. | Grep `/home/sp3ct0r` | Replaced all developer machine paths with portable placeholders across all documentation and examples. | FIXED | `610d46b` |
| **H2** | P1 | Hygiene | Six overlapping doc files with duplicate information. | Repo root | Consolidated into `README.md`, `RUNBOOK.md`, `SECURITY.md`, and concise `AGENTS.md` (43 lines). Deleted `PLAN.md` and `docs/FACTORY_GUIDE.md`. | FIXED | `610d46b` |
| **H3** | P1 | Hygiene | Missing standard OSS/business files: LICENSE, SECURITY.md, CHANGELOG.md, CI, pre-commit, .editorconfig. | Repo root | Added MIT `LICENSE`, `SECURITY.md`, `CHANGELOG.md`, `.github/workflows/ci.yml`, `.editorconfig`, `.pre-commit-config.yaml`. | FIXED | `610d46b` |
| **H4** | P2 | Hygiene | `bootstrap-repo.sh` copied mandates into workspace and wrote Python-only README. | `bootstrap-repo.sh` | Removed redundant mandate copying and made workspace template language-neutral. | FIXED | `610d46b` |
| **H5** | P2 | Hygiene | `.gitignore` missing coverage and log directories. | `.gitignore` | Added `.coverage`, `htmlcov`, `factory.kill`. | FIXED | `610d46b` |
| **H6** | P2 | Hygiene | Release hygiene: SemVer version bump, CHANGELOG, accurate capability claims. | `pyproject.toml`, `README.md` | Bumped version to `0.3.0`, created `CHANGELOG.md`, and aligned prompt-driven capability claims. | FIXED | `610d46b` |
| **H7** | P2 | Hygiene | Missing business documentation: data privacy statement, cost models, limits. | Docs | Documented Featherless/Band data transmission disclosures, cost guardrails, and operational limitations in `README.md`. | FIXED | `610d46b` |
| **H8** | P2 | Hygiene | Dual-gate was prompt-only; missing deterministic verification script. | Mandates | Created `scripts/verify-milestone.sh` (<60 lines) verifying commit existence, clean tree, and test exit codes. | FIXED | `610d46b` |

---

## 3. Decisions Log

- **D1 (ECC Scope):** ECC remains dev-time tooling for operator workflow and repo maintenance; mandates run as self-contained prompts in OpenCode seats.
- **D2 (Pager Fallback):** Configured git `core.pager = cat` whenever `less` is missing to ensure non-interactive script stability.
- **D3 (Package Structure):** Structured `src/factory` as a clean, installable package with module entry points and thin backward-compatible shims in `src/`.
- **D4 (Documentation Consolidation):** Consolidated documentation into 4 core files: `README.md` (overview/quickstart), `RUNBOOK.md` (operations), `SECURITY.md` (threat model/reporting), `AGENTS.md` (concise 43 lines Antigravity instructions). Deleted `PLAN.md` and `docs/FACTORY_GUIDE.md`. Reduced `CLAUDE.md` to a single-line pointer.
- **D5 (License Decision):** MIT License with copyright "2026 RafalW3bCraft <thewhitefalcon13@proton.me>".
- **D6 (Provider Testing Mode):** Hermetic testing by default; opt-in live provider verification with `TEST_LIVE=1`.
- **D7 (Provider & Model Pinning):** Retained Featherless AI + Band SDK (`zai-org/GLM-5.3-Flash`, `MiniMaxAI/MiniMax-M2.5`).
- **D8 (Git Remote):** Push `hardening/prod-ready` to origin once verification gate passes.
- **D9 (Filesystem Scope):** Permitted isolated scratch/temp usage in `/tmp` for hermetic testing.

---

## 4. Accepted Risks & Operational Boundaries

1. **LLM Non-Determinism (Accepted Risk):** Model completions from Featherless AI are inherently non-deterministic. Dual-gate verification provides behavioral verification (tests pass, SAST clean, DAST resilient), but cannot formally guarantee mathematical absence of unknown bugs.
2. **Provider Key In-Flight Transmission (Accepted Risk):** Prompts and workspace code diffs are transmitted over HTTPS to Featherless AI and Band platform. Operators processing highly sensitive intellectual property must ensure organizational compliance with Featherless AI and Band Terms of Service.
3. **Single-Operator Operating Model (Scope Boundary):** Multi-tenant SaaS isolation is logged as out-of-scope per system assumptions. Dark Factory is designed for a single operator running on their dedicated machine or server.
