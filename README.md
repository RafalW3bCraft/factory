# Dark Factory — Autonomous Multi-Agent Software & Cybersecurity Engineering

Dark Factory is an autonomous multi-agent software engineering, cybersecurity assessment, and digital forensics system powered by **Band SDK**, **OpenCode**, and the **Everything Claude Code (ECC)** methodology.

Four specialized LLM seats collaborate within an isolated workspace repository:
- **@Foreman**: System Architecture, Task Planning, STRIDE Threat Modeling & Multi-Agent Coordination
- **@Smith**: Full-Stack Construction, Secure Coding by Design, Test-Driven Development (TDD) & Defect Remediation
- **@Inspector**: Independent Review, Static Application Security Testing (SAST), Code Forensics & OWASP Top 10 Auditing
- **@Stresser**: Dynamic Application Security Testing (DAST), Adversarial Fuzzing, Concurrency & Load Stress, Crash Forensics

---

## Architecture & Seat Overview

```
                      ┌────────────────────────────┐
                      │    Operator / Human        │
                      └─────────────┬──────────────┘
                                    │ Single Dispatch (No mid-run prompts)
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

## Directory Layout

```
factory/
├── start-factory.sh          Starts OpenCode server + launches the 4 supervised seats
├── stop-factory.sh           Gracefully terminates OpenCode and seat processes
├── preflight.sh              Comprehensive diagnostics & system readiness validation
├── bootstrap-repo.sh         Bootstraps a fresh workspace git repository
├── render-dispatch.sh        CLI to render Foreman mission briefs with parameter tokens
├── mandates/                 Operating seat instructions with Harness and Model headers
├── dispatch/                 Mission templates for engineering, security, and forensics
├── src/                      Core runner (run_seat.py), linter, analyzer, and dispatch engine
├── tests/                    Pytest automated test suite
├── docs/                     Architecture decisions and operational guides
├── workspace/                Default local workspace git repository
└── .agents/                  ECC skills, agents, rules, and workflows (affaan-m)
```

---

## Prerequisites & Setup

### 1. Requirements
- Python 3.12+ and `uv`
- OpenCode (`~/.opencode/bin/opencode` or on PATH)
- BAND CLI / BAND Desktop
- Featherless AI API key (for OpenCode provider)

### 2. Quick Setup

```bash
# 1. Install / sync dependencies into virtual environment
uv sync

# 2. Make shell scripts executable
chmod +x ./*.sh

# 3. Configure local environment
cp .env.example .env
chmod 600 .env
# Set FEATHERLESS_API_KEY and RESULT_REPO in .env

# 4. Configure Band credentials
cp agent_config.example.yaml agent_config.yaml
chmod 600 agent_config.yaml
# Populate external agent IDs and keys generated in Band Desktop
```

---

## Verification & Diagnostics

Run the integrated preflight diagnostics to verify tooling, Python virtualenv, credentials, models, and test suite:

```bash
./preflight.sh
```

Run tests directly:

```bash
uv run pytest -v
```

---

## Launching a Mission

### 1. Bootstrap Target Repository
```bash
./bootstrap-repo.sh /home/sp3ct0r/factory/workspace
```

### 2. Render Mission Dispatch
Choose a mission template or provide a custom task description:

```bash
# Full-Stack Engineering Mission
./render-dispatch.sh engineering --task "Build secure REST API with JWT auth and rate limiting"

# Cybersecurity Audit & Hardening Mission
./render-dispatch.sh security    --task "Perform OWASP Top 10 security audit on api/ and remediate findings"

# Crash Analysis & Digital Forensics Mission
./render-dispatch.sh forensics   --task "Isolate root cause of worker deadlocks under load and fix"
```

### 3. Start the Factory
```bash
RESULT_REPO=/home/sp3ct0r/factory/workspace ./start-factory.sh
```

Paste the rendered dispatch message into the lead room for `@Foreman`. The factory will execute autonomously in dark-factory mode until Foreman delivers the verified final report.

### 4. Stop the Factory
```bash
./stop-factory.sh
```

### 5. Session Post-Mortem & Room Analysis
Analyze agent teamwork, mention flows, caught defects, and commit history from the exported room log:

```bash
python3 src/analyze_room.py room.json --repo /home/sp3ct0r/factory/workspace
```
