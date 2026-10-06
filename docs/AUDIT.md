# Factory Hardening Audit Ledger

## 1. Baseline Measurements (2026-10-06)

Branch: `hardening/prod-ready`  
Baseline commit: `e449c7f`  

### Tracked Files & Storage Footprint
| Directory | Tracked Files | Total Bytes | KB / MB | Notes |
|---|---|---|---|---|
| `(root)` | 16 | 302,677 B | 295.6 KB | Core configs, shell scripts, docs |
| `.agents/` | 707 | 4,778,742 B | 4,666.7 KB (4.67 MB) | Bloated ECC install (68 agents, 122 rules, 280 skills, 94 workflows) |
| `dispatch/` | 3 | 5,591 B | 5.5 KB | 3 mission templates |
| `docs/` | 1 | 4,547 B | 4.4 KB | Technical guide |
| `mandates/` | 4 | 19,612 B | 19.2 KB | 4 seat mandates |
| `src/` | 5 | 22,210 B | 21.7 KB | Python factory sources |
| `tests/` | 2 | 2,797 B | 2.7 KB | Test suite |
| **Total Baseline** | **738** | **5,136,176 B** | **4.90 MB** | Baseline before ECC prune and hardening |

### Quality & Verification Baseline
- **`uv sync --frozen`**: Exit 0 (`Checked 50 packages in 1ms`).
- **`uv run pytest -q`**: Exit 0 (`9 passed in 0.03s`).
- **Test Coverage of `src/`**: **14.6%** (68 / 466 lines covered):
  - `analyze_room.py`: 0.0% (0 / 156)
  - `lint_mandates.py`: 62.2% (46 / 74)
  - `render_dispatch.py`: 0.0% (0 / 95)
  - `run_seat.py`: 16.5% (22 / 133)
  - `factory/__init__.py`: 0.0% (0 / 8)
- **`ruff check .`**: Exit 0 (`All checks passed!`).
- **`ruff format --check .`**: Exit 1 (`4 files would be reformatted`: `src/analyze_room.py`, `src/lint_mandates.py`, `src/render_dispatch.py`, `tests/test_mandates.py`).
- **`mypy src tests`**: Exit 1 (2 errors in `src/analyze_room.py:151`, `src/analyze_room.py:152` — variable `c` reused with conflicting types `Counter` vs `int`).
- **`bash -n *.sh`**: Exit 0 (Valid shell syntax).
- **`shellcheck *.sh`**: Exit 1 (5 warnings across `preflight.sh` and `start-factory.sh`: SC2015, SC1090, SC1091, SC2034).
- **Vulnerability scan (`pip-audit`)**: Exit 0 (`No known vulnerabilities found` across 29 environment packages).
- **Secret scan (`detect-secrets`)**: Exit 0 (Zero real secrets in tracked files; false positives on ECC docs and `agent_config.example.yaml` placeholders).

---

## 2. Findings Ledger

| ID | Sev | Area | Summary | Evidence / Command | Fix Plan | Status | Commit |
|---|---|---|---|---|---|---|---|
| **S1** | P0 | Security | `run_seat.py` uses `approval_mode="auto_accept"` granting unsandboxed root/host execution to LLM tool calls. | `run_seat.py:132` | Containerize / sandbox execution (Docker/Podman / non-root / restricted mounts and egress). | OPEN | - |
| **S2** | P0 | Security | Credential exposure: `FEATHERLESS_API_KEY` and all Band seat credentials readable across processes/seats. | `start-factory.sh:75`, `agent_config.yaml` | Process isolation, per-seat secret injection, prevent seats from reading parent env/keys. | OPEN | - |
| **S3** | P1 | Security | `source .env` executes arbitrary shell commands. | `start-factory.sh:75`, `preflight.sh:89` | Replace with safe, hardened `KEY=VALUE` parser. | OPEN | - |
| **S4** | P1 | Security | `preflight.sh` passes API key in `curl` argv, visible in `/proc` and `ps`. | `preflight.sh:101` | Pass Authorization header via stdin (`--header @-`) or temp config. | OPEN | - |
| **S5** | P2 | Security | OpenCode server on `127.0.0.1:4096` unauthenticated. | `start-factory.sh:134` | Add OpenCode token/password auth, configurable port, fail-closed check. | OPEN | - |
| **S6** | P1 | Security | Untrusted prompt injection boundary between repo data and mandates. | Mandates / Stresser | Explicit prompt trust boundaries; technical egress backstop for Stresser. | OPEN | - |
| **S7** | P2 | Security | Missing supply chain hygiene & automated security scans. | CI / repo | Add GitHub Actions CI with pip-audit, gitleaks, Dependabot/Renovate. | OPEN | - |
| **R1** | P1 | Reliability | Supervisor watchdog uses lifetime-per-seat counter, deadlocking if Foreman fails. | `start-factory.sh:199` | Windowed restarts, seat backoff, fail-fast supervisor exit on critical seats. | OPEN | - |
| **R2** | P1 | Reliability | No mission-level wall-clock timeout or kill switch. | `start-factory.sh` | Add mission-level deadline, turn limits, and documented kill switch. | OPEN | - |
| **R3** | P2 | Reliability | Logs overwritten unconditionally on start; no log rotation. | `start-factory.sh:168` | Run-isolated log directories `logs/<run-id>/` with `latest` symlink and retention. | OPEN | - |
| **R4** | P2 | Reliability | `stop-factory.sh` uses unconditional `kill -9` without process groups. | `stop-factory.sh:37` | Use process groups (`set -m`, `kill -- -PID`), grace period, consistent cmdline verification. | OPEN | - |
| **R5** | P2 | Reliability | Hardcoded port 4096, provider "featherless", and base_url scattered. | `start-factory.sh`, `run_seat.py` | Centralized validated configuration surface. | OPEN | - |
| **R6** | P1 | Reliability | Preflight doesn't verify mandate models exist in provider catalog; test asserts literal model names. | `preflight.sh:106`, `test_mandates.py:17` | Preflight model verification; single source of truth in mandates. | OPEN | - |
| **R7** | P3 | Reliability | `preflight.sh` header promises 8 checks but prints `[n/7]`, imports pytest in runtime check. | `preflight.sh:36` | Align header count, separate runtime preflight from dev-time test suite. | OPEN | - |
| **Q1** | P1 | Quality | Coverage is 14.6% on `src/` (target >= 85%). | Trace baseline | Comprehensive behavior test suite for all modules and CLI scripts. | OPEN | - |
| **Q2** | P2 | Quality | `mypy` 2 errors in `analyze_room.py`; `ruff format` touches 4 files. | `mypy src tests`, `ruff format` | Fix type annotations and enforce formatting in CI. | OPEN | - |
| **Q3** | P2 | Quality | `src/` scripts outside package, `sys.path.insert` in tests, stub `factory:main`. | `pyproject.toml`, `tests/` | Clean packaging with `python -m factory.<module>` or direct entrypoints. | OPEN | - |
| **Q4** | P2 | Quality | `render_dispatch` custom env loader; `analyze_room` heuristic regexes and hand-rolled argv. | `src/render_dispatch.py` | Use `python-dotenv` and `argparse`; fixture tests. | OPEN | - |
| **Q5** | P3 | Quality | `die()` untyped `NoReturn`; print debugging instead of logging. | `src/run_seat.py` | Type annotations (`NoReturn`) and structured `logging`. | OPEN | - |
| **H1** | P1 | Hygiene | Machine-specific paths hardcoded in docs, examples, and ECC state. | Grep `/home/sp3ct0r` | Relative paths and portable placeholders everywhere. | OPEN | - |
| **H2** | P1 | Hygiene | Six overlapping doc files with duplicate information. | `README`, `AGENTS`, `CLAUDE`, `PLAN`, `RUNBOOK`, `FACTORY_GUIDE` | Consolidate: `README.md`, `RUNBOOK.md`, `SECURITY.md`, `AGENTS.md` (<=80 lines). | OPEN | - |
| **H3** | P1 | Hygiene | Missing standard OSS/business files: LICENSE, SECURITY.md, CHANGELOG.md, CI workflows, pre-commit. | Repo root | Create standard files and GitHub Actions CI. | OPEN | - |
| **H4** | P2 | Hygiene | `bootstrap-repo.sh` redundant mandate copy and Python-only README. | `bootstrap-repo.sh` | Clean, language-neutral workspace bootstrap. | OPEN | - |
| **H5** | P2 | Hygiene | `.gitignore` missing coverage and log directories. | `.gitignore` | Add `.coverage`, `htmlcov`, per-run log dirs. | OPEN | - |
| **H6** | P2 | Hygiene | Release hygiene: SemVer, CHANGELOG, accurate capability claims. | `pyproject.toml`, `README.md` | Align claims with code capabilities; SemVer version bump. | OPEN | - |
| **H7** | P2 | Hygiene | Missing business documentation: data privacy statement, cost models, limits. | Docs | Add data handling statement and SLA/limitations documentation. | OPEN | - |
| **H8** | P2 | Hygiene | Dual-gate is prompt-only; missing deterministic verification script. | Mandates | Add deterministic verifier script (`verify-milestone.sh`). | OPEN | - |
| **E1** | P0 | ECC | `.agents` bloated (707 files, 4.67 MB, 68 agents, 122 rules, 280 skills, 94 workflows). Leaks machine paths; rules lack Antigravity triggers. | `.agents` | Reinstall curated ECC subset matching budget (<=12 rules with triggers, <=12 agents, <=25 skills, 0 workflows). | FIXED | 8e029c1 |

---

## 3. Decisions Log

- **D1 (ECC Scope):** ECC remains dev-time tooling for operator workflow and repo maintenance; mandates run as self-contained prompts in OpenCode seats.
- **D2 (Pager Fallback):** Configure git `core.pager = cat` whenever `less` is missing to ensure non-interactive script stability.
- **D3 (Package Structure):** Structure `src/factory` as a clean, installable package with module entry points, eliminating `sys.path.insert`.
- **D4 (Documentation Consolidation):** Consolidate documentation into 4 core files: `README.md` (overview/quickstart), `RUNBOOK.md` (operations), `SECURITY.md` (threat model/reporting), `AGENTS.md` (concise <=80 lines Antigravity instructions).
- **D5 (License Decision):** MIT License with copyright "2026 RafalW3bCraft <thewhitefalcon13@proton.me>".
- **D6 (Provider Testing Mode):** Hermetic testing by default; opt-in live provider verification with `TEST_LIVE=1`.
- **D7 (Provider & Model Pinning):** Retain Featherless AI + Band SDK (`zai-org/GLM-5.3-Flash`, `MiniMaxAI/MiniMax-M2.5`).
- **D8 (Git Remote):** Push `hardening/prod-ready` to origin once verification gate passes.
- **D9 (Filesystem Scope):** Permitted isolated scratch/temp usage in `/tmp` for hermetic testing.
