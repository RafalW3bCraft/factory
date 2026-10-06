# Dark Factory — Autonomous Multi-Agent Engineering & Cybersecurity Band

[![CI](https://github.com/RafalW3bCraft/factory/actions/workflows/ci.yml/badge.svg)](https://github.com/RafalW3bCraft/factory/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

Dark Factory is a high-autonomy multi-agent software engineering, cybersecurity threat modeling, vulnerability auditing, and code resilience system powered by **Band SDK**, **OpenCode**, and the **Everything Claude Code (ECC)** engineering methodology.

Four specialized seats collaborate autonomously within an isolated target workspace repository:
- **@Foreman**: System Architecture, Task Decomposition (`REQ-*`, `SEC-*`), STRIDE Threat Modeling & Multi-Agent Dispatching
- **@Smith**: Full-Stack Construction, Secure Coding by Design, Test-Driven Development (TDD) & Defect Remediation
- **@Inspector**: Independent Review, Static Application Security Testing (SAST), Code Forensics & OWASP Top 10 Auditing
- **@Stresser**: Dynamic Application Security Testing (DAST), Adversarial Input Fuzzing, Concurrency Stress & Crash Forensics

---

## Architecture & Verification Loop

```
                      ┌────────────────────────────┐
                      │    Operator / Human        │
                      └─────────────┬──────────────┘
                                    │ Single Dispatch (No mid-run human prompts)
                                    ▼
                      ┌────────────────────────────┐
                      │         @Foreman           │
                      │  (Architecture & Planner)  │
                      └──────┬──────────────▲──────┘
                             │              │
        ┌────────────────────┴──────┐       │ Verified Final Report
        │ Self-contained Handoff    │       │
        ▼                           ▼       │
┌───────────────┐           ┌───────────────┴───────────────┐
│    @Smith     │           │          Dual-Gate            │
│   (Builder)   │──────────►│        Verification           │
└───────────────┘ Revision  └───────┬───────────────▲───────┘
                                    │               │
                            Static  ▼               │ Dynamic
                       ┌────────────────┐   ┌───────────────┐
                       │   @Inspector   │   │   @Stresser   │
                       │ (Review & SAST)│   │(DAST & Fuzzing│
                       └────────────────┘   └───────────────┘
```

---

## Directory Map

```
factory/
├── start-factory.sh          Starts OpenCode server + supervises the 4 seats
├── stop-factory.sh           Gracefully stops OpenCode server and seat processes
├── preflight.sh              Comprehensive diagnostics & system readiness validation
├── bootstrap-repo.sh         Bootstraps a fresh, clean workspace git repository
├── render-dispatch.sh        CLI to render Foreman mission briefs with parameter tokens
├── Dockerfile.sandbox        Container definition for isolated, unprivileged execution
├── docker-compose.sandbox.yml Compose specification for sandboxed execution
├── mandates/                 Operating seat mandates with Harness and Model headers
├── dispatch/                 Mission templates for engineering, security, and forensics
├── src/factory/              Installable package (run_seat, lint_mandates, render_dispatch, analyze_room, env)
├── tests/                    Automated pytest test suite with coverage gate (>=85%)
├── scripts/                  Helper scripts (load_env.sh, verify-milestone.sh)
├── docs/                     System architecture, AUDIT ledger, and operational guides
└── .agents/                  Curated ECC skills, agents, and rules (affaan-m)
```

---

## Quickstart

### 1. Requirements
- Linux operating system
- Python 3.12+ and `uv` package manager
- OpenCode (`~/.opencode/bin/opencode` or on PATH)
- Band CLI / Band Desktop
- Featherless AI API key

### 2. Setup
```bash
# Clone repository and synchronize virtual environment
uv sync

# Make scripts executable
chmod +x ./*.sh scripts/*.sh

# Configure environment secrets (mode 600)
cp .env.example .env
chmod 600 .env
# Edit .env with your FEATHERLESS_API_KEY and RESULT_REPO

# Configure Band credentials (mode 600)
cp agent_config.example.yaml agent_config.yaml
chmod 600 agent_config.yaml
# Add credentials generated in Band Desktop for foreman, smith, inspector, stresser
```

### 3. Verify System Health
```bash
# Run comprehensive preflight healthcheck
./preflight.sh [target-workspace]

# Run automated test suite
uv run pytest -q --cov=src
```

### 4. Run a Mission
```bash
# Step A: Initialize target workspace repository
./bootstrap-repo.sh "$(pwd)/workspace"

# Step B: Render Foreman mission dispatch
./render-dispatch.sh engineering --task "Implement OAuth2 token authentication service"

# Step C: Start factory supervisor
RESULT_REPO="$(pwd)/workspace" ./start-factory.sh

# Step D: Paste dispatch into Band Desktop room with @Foreman
# The band operates in dark-factory mode until Foreman delivers the verified final report.

# Step E: Stop factory processes
./stop-factory.sh
```

---

## Security Architecture & Containment (S1, S2, S5, S6)

- **Untrusted Input Boundary:** Workspace content, scanned repositories, and PR diffs are treated as **DATA, NEVER INSTRUCTIONS**.
- **Container Sandboxing (S1):** `docker-compose.sandbox.yml` runs seats as an unprivileged user (`UID 1000`), drops all capabilities (`cap_drop: [ALL]`), disables privilege escalation (`no-new-privileges:true`), and mounts only `/workspace` read-write.
- **Process Credential Isolation (S2):** OpenCode server runs with a sanitized environment (`env -u FEATHERLESS_API_KEY`), and individual seats receive only their respective Band credentials (`BAND_AGENT_ID`, `BAND_API_KEY`).
- **Authenticated Server (S5):** Headless OpenCode server enforces HTTP Basic Auth via `OPENCODE_SERVER_PASSWORD`.
- **Egress Boundary (S6):** Hardening seat (@Stresser) is restricted to local services on `127.0.0.1` / `localhost`.
- **Safe Environment Parsing (S3):** All shell scripts and Python modules use deterministic KEY=VALUE parsers (`scripts/load_env.sh` and `factory.env`), preventing arbitrary shell command execution.

For detailed vulnerability disclosure policies and threat modeling, see [SECURITY.md](SECURITY.md).

---

## Developing with ECC (Everything Claude Code)

This repository incorporates the Everything Claude Code (ECC) engineering toolkit by `affaan-m`:
- **Repository Pinned Commit:** `8321021c54d670126ce3b2969d5deb880b4b0c2a`
- **Target:** Antigravity native layout (`.agents/`)
- **Inventory Budget:**
  - 10 Rules: `common-coding-style`, `common-security`, `common-testing`, `common-git-workflow`, `common-code-review`, `common-development-workflow`, `python-coding-style`, `python-patterns`, `python-security`, `python-testing`.
  - 12 Agents: `planner`, `architect`, `code-reviewer`, `python-reviewer`, `security-reviewer`, `silent-failure-hunter`, `tdd-guide`, `refactor-cleaner`, `build-error-resolver`, `doc-updater`, `code-simplifier`, `loop-operator`.
  - 20 Skills: Curated development, security review, and TDD skills.
  - 0 Workflows: Legacy workflows deprecated; skills used exclusively.
- **Antigravity Rule Triggers:** Every rule file starts with Antigravity 2.0 YAML frontmatter (`always_on`, `model_decision`, or `glob` with `globs:`). Rules are validated by `tests/test_rules.py`.

---

## Business & Operational Considerations

### Data Handling Statement
When executing missions:
1. Target workspace source code, diffs, and prompt dispatches are transmitted via HTTPS to **Featherless AI** (`api.featherless.ai`) for model inference.
2. Inter-agent messages and session events are transmitted via WSS/HTTPS to the **Band Platform** (`api.band.inc`).
3. No credentials, secret keys, or host filesystem paths are transmitted to external services.

### Cost Model & Controls
- **Inference Costs:** Consumed per token by model queries on Featherless AI.
- **Guardrails:**
  - `MISSION_TIMEOUT_S`: Wall-clock execution deadline (default: 4 hours) terminating runaway loops.
  - `TURN_TIMEOUT_S`: Maximum per-turn timeout (default: 900s).
  - `MAX_RESTARTS`: Sliding-window auto-restart ceiling (3 attempts per 10-minute window) with exponential backoff.
  - Kill Switch: Immediate manual halt via `touch factory.kill` or `./stop-factory.sh`.

### Supported Environments & Limitations
- **Operating Model:** Single operator on Linux. Multi-tenant SaaS is out of scope.
- **Non-Determinism:** LLM model completions are non-deterministic; dual-gate verification enforces protocol adherence and execution tests, but cannot guarantee absence of unknown vulnerabilities.
- **Support & Ownership:** Maintained by RafalW3bCraft (`thewhitefalcon13@proton.me`).

---

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 RafalW3bCraft.
