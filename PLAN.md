# Dark Factory — System Architecture & Evolutionary Plan

This document outlines the architectural roadmap, design principles, and operational
strategy for the autonomous multi-agent Dark Factory.

---

## 1. System Vision & Paradigm

The Dark Factory operates as a "lights-out" autonomous software development and
cybersecurity engineering facility. Given a human objective (dispatch), the multi-agent
band self-orchestrates to plan, construct, review, fuzz, and verify code without
intermediate human steering.

### Core Tenets
1. **Separation of Concerns:**
   - @Foreman: Architecture, threat modeling, decomposition, triage.
   - @Smith: Full-stack construction, secure coding, TDD implementation.
   - @Inspector: Independent static analysis, SAST, code forensics, quality audit.
   - @Stresser: Dynamic resilience, DAST, fuzzing, concurrency stress, crash forensics.
2. **Dual-Gate Verification:**
   Code is never merged or accepted without independent static review clearance from
   @Inspector and dynamic resilience verification from @Stresser.
3. **Evidence-Based Traceability:**
   Every requirement (REQ-*, SEC-*, CRASH-*) must trace directly to reproducible
   execution logs and test outcomes.
4. **Security & Forensics by Default:**
   Cybersecurity is not an afterthought: threat modeling begins with Foreman, secure
   coding is enforced by Smith, SAST is audited by Inspector, and dynamic fuzzing &
   crash reproduction are conducted by Stresser.

---

## 2. Architecture & Communication Protocol

### The Dark Factory Protocol
- **Dark Runs:** The human dispatch initiates the work. No mid-run confirmation dialogs
  or human steering are permitted.
- **Self-Contained Handoffs:** Agents see only messages addressed to them. Every
  handoff includes complete requirements, git revisions, repository paths, and test commands.
- **Supervision & Watchdog:** `start-factory.sh` monitors agent processes via PIDs and
  automatically recovers from transient network/seat crashes up to `MAX_RESTARTS`.

---

## 3. Integration with Everything Claude Code (ECC)

Located in `.agents/`, ECC provides industry-grade skills, agents, and rules:
- **TDD Guidance:** Enforces test-first development and regression safety.
- **Static Security Auditing:** Enforces OWASP Top 10 defenses, CWE checks, and least privilege.
- **Silent Failure Hunting:** Surfaces unhandled errors, swallowed exceptions, and race conditions.
- **Refactoring & Clean Architecture:** Keeps dependencies decoupled and code idiomatic.

---

## 4. Current State & Verification Milestones

- [x] Hackathon and submission cruft eliminated (slides, stage mocks, competition gates removed).
- [x] Mandate files upgraded for all 4 seats (architecture, secure coding, SAST, DAST, forensics).
- [x] Dynamic dispatch templating engine operational (`render-dispatch.sh`, `render_dispatch.py`).
- [x] Comprehensive preflight diagnostics implemented (`preflight.sh`).
- [x] Automated test suite passing (pytest).
- [x] Featherless AI live provider authenticated and verified (HTTP 200).
- [x] OpenCode and Band SDK integrated and verified.
- [x] Workspace repository bootstrapped and operational.
