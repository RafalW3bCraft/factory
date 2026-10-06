# Dark Factory — Autonomous Multi-Agent Engineering & Cybersecurity System

## System Purpose
A high-autonomy multi-agent development and security engineering band running
four specialized seats (Foreman, Smith, Inspector, Stresser) via the Band SDK
and OpenCode, augmented with the Everything Claude Code (ECC) engineering methodology.

Targeted for personalized full-stack development, architectural design, cybersecurity
threat modeling, static/dynamic vulnerability assessment, and digital code forensics.

## Directory Map

```
factory/
├── start-factory.sh          Start OpenCode server + supervise all 4 seats
├── stop-factory.sh           Clean shutdown of factory processes by PID
├── preflight.sh              Comprehensive environment, model, & repository diagnostics
├── bootstrap-repo.sh         Initialize a fresh, clean target workspace git repository
├── render-dispatch.sh        Render Foreman mission dispatches (engineering, security, forensics)
├── mandates/                 Operating mandates per seat (Harness: OpenCode + Model: headers)
│   ├── foreman.md            Lead: Architecture, threat modeling, task planning, triage
│   ├── smith.md              Builder: Full-stack coding, secure coding, TDD, remediation
│   ├── inspector.md          Reviewer: SAST, code review, OWASP security audit, forensics
│   └── stresser.md           Hardening: DAST, adversarial fuzzing, concurrency, crash forensics
├── dispatch/                 Mission templates with token substitution
│   ├── software-engineering.md.tmpl
│   ├── security-audit.md.tmpl
│   └── forensics-crash.md.tmpl
├── src/
│   ├── factory/              Package entry points and stubs
│   ├── run_seat.py           CLI runner: validates mandate & connects one Band seat
│   ├── lint_mandates.py      Mandate header, model, and secret hygiene validator
│   ├── render_dispatch.py    Dispatch rendering engine with token replacement
│   └── analyze_room.py       Band room session analyzer (messages, mentions, interventions)
├── tests/                    Pytest suite for factory tooling and mandates
├── docs/                     System architecture, operator runbooks, and design guides
├── workspace/                Default local result git repository
├── pyproject.toml            Python package dependencies (uv-managed)
├── agent_config.example.yaml Template for Band external agent IDs and API keys
└── .env.example              Template for local API keys and paths
```

## The Four Seats & Capabilities

| Seat | Role | Model | Core Capabilities |
|---|---|---|---|
| **@Foreman** | Lead Orchestrator & Architect | `zai-org/GLM-5.3-Flash` | System design, task decomposition (REQ-*), STRIDE threat modeling, forensic incident triage, multi-agent dispatching |
| **@Smith** | Full-Stack Builder & Security Coder | `zai-org/GLM-5.3-Flash` | Multi-language engineering, TDD test suites, OWASP-compliant secure coding, surgical defect & vulnerability remediation |
| **@Inspector** | Independent Reviewer & SAST Auditor | `MiniMaxAI/MiniMax-M2.5` | Independent test reproduction, Static Application Security Testing (SAST), code quality review, digital code forensics |
| **@Stresser** | Hardening Engineer & Crash Analyst | `zai-org/GLM-5.3-Flash` | Dynamic Application Security Testing (DAST), input fuzzing, race condition & concurrency stress, crash reproduction forensics |

## ECC (Everything Claude Code) Integration

The repository incorporates ECC (`affaan-m`) workflows located in `.agents/`:
- **Planning & Architecture:** ECC `planner` and `architect` patterns are mirrored in @Foreman.
- **TDD & Secure Implementation:** ECC `tdd-guide`, `build-error-resolver`, and language-specific resolvers are mirrored in @Smith.
- **Code & Security Review:** ECC `code-reviewer`, `security-reviewer`, and `silent-failure-hunter` patterns are mirrored in @Inspector.
- **Adversarial Resilience:** ECC GAN evaluator and dual-review convergence loops are mirrored in @Stresser.

## Operational Rules & Safety Discipline

1. **No Secrets in Version Control:**
   - Never print, log, commit, or leak values from `.env`, `agent_config.yaml`, or OpenCode configuration.
   - Mandates and dispatches are scanned by `lint_mandates.py` to prevent credential exposure.
2. **Autonomous Dark Operation:**
   - Seats resolve requirements from specifications and repository evidence without human hand-holding.
   - Handoffs between seats are 100% self-contained.
3. **Dual-Gate Verification:**
   - No code or task is marked accepted without BOTH @Inspector static review clearance AND @Stresser dynamic resilience verification.
4. **Local Sandboxing:**
   - Dynamic probing and fuzzing are strictly confined to local test sandboxes and localhost services. External hosts are never targeted.
5. **Deterministic Verification:**
   - All claims of passing checks require reproduced command executions with verified exit codes and logs.
6. **Clean Commits:**
   - Commit changes using Conventional Commits (`feat`, `fix`, `refactor`, `test`, `security`).

## Quickstart & Verification

```bash
# 1. Run environment diagnostics and health checks
./preflight.sh

# 2. Run automated test suite
uv run pytest -v

# 3. Render a dispatch for Foreman
./render-dispatch.sh engineering --task "Implement secure user authentication API"
./render-dispatch.sh security    --task "Perform OWASP Top 10 audit on api/ routes"
./render-dispatch.sh forensics   --task "Isolate and fix race condition in worker queue"

# 4. Start the factory band
RESULT_REPO=/home/sp3ct0r/factory/workspace ./start-factory.sh

# 5. Stop the factory band
./stop-factory.sh
```
