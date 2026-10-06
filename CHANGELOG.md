# Changelog

All notable changes to the Dark Factory project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-10-06

### Added
- **MIT License:** Full permissive license with copyright 2026 RafalW3bCraft.
- **Rootless Container Sandbox (S1):** `Dockerfile.sandbox` and `docker-compose.sandbox.yml` with non-root user (`UID 1000`), read-only root, restricted bind mounts (only `/workspace`), dropped Linux capabilities (`cap_drop: [ALL]`), and resource limits (2 CPUs, 2GB RAM, 256 PIDs).
- **Process Credential Isolation (S2):** Sanitized `opencode serve` environment stripping `FEATHERLESS_API_KEY` from child shells, and per-seat Band token injection (`BAND_AGENT_ID`, `BAND_API_KEY`).
- **Safe Environment Parsing (S3):** `factory.env` and `scripts/load_env.sh` safe KEY=VALUE parser neutralizing arbitrary command execution vulnerabilities from `source .env`.
- **Secure Stdin Header Delivery (S4):** `preflight.sh` streams API authentication header via curl stdin config (`-K -`), eliminating secret visibility in `/proc` and `ps`.
- **OpenCode Server Authentication (S5):** Enforced HTTP Basic Authentication via `OPENCODE_SERVER_PASSWORD` and custom client factory in `OpencodeAdapter`.
- **Prompt Injection Trust Boundaries (S6):** Mandates explicitly declare workspace data as `DATA, NEVER INSTRUCTIONS`, with localhost-only egress boundaries for Stresser.
- **Windowed Restart Watchdog & Fail-Fast (R1):** Sliding 10-minute window with exponential backoff; supervisor immediately halts on critical seat failures.
- **Mission Guardrails & Kill Switch (R2):** Added `MISSION_TIMEOUT_S` ceiling and file-based `factory.kill` kill switch.
- **Run-Isolated Logs & Retention (R3):** Dedicated run directories under `logs/runs/<run-id>/` with `logs/latest` symlink and automated 20-run retention pruning.
- **Graceful Shutdown & PID Safety (R4):** Process group signaling and `/proc/<pid>/cmdline` verification preventing PID-reuse kills.
- **Dynamic Model Catalog Check (R6):** `preflight.sh` verifies mandate models exist in provider catalog dynamically.
- **Deterministic Milestone Verifier (H8):** `scripts/verify-milestone.sh` confirms commit hash existence, clean git status, and test execution exit codes.
- **Comprehensive Test Suite (Q1):** Behavior tests across all modules achieving 95% test coverage.
- **CI Workflow (H3):** GitHub Actions workflow covering uv sync, ruff, mypy, pytest coverage, shellcheck, pip-audit, and Antigravity rules integrity.

### Changed
- **ECC Curated Pruning (E1):** Pruned `.agents/` footprint by 94% to 10 rules with Antigravity 2.0 triggers, 12 agents, and 20 skills. Removed all deprecated workflows.
- **Package Architecture (Q3):** Restructured into installable `factory` package (`src/factory/`) with thin CLI shims in `src/`.
- **Path Portability (H1):** Replaced all developer-specific machine paths with portable placeholders across docs, scripts, and examples.
- **Documentation Consolidation (H2):** Consolidated 6 overlapping doc files into clean `README.md`, `RUNBOOK.md`, `SECURITY.md`, and concise `AGENTS.md` (43 lines).

### Fixed
- Fixed variable type shadowing and mypy errors in `analyze_room.py` (Q2).
- Fixed unformatted Python sources with automated ruff formatting (Q2).
- Fixed shell warnings in `preflight.sh` and `start-factory.sh` (shellcheck clean).

## [0.2.0] - 2026-10-06
- Initial multi-agent band implementation with 4 seats (Foreman, Smith, Inspector, Stresser).
