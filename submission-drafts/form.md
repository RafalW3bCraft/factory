# Hackathon Submission Form Copy

## Project Title
Pocketful Factory: A Four-Seat Dark Factory That Proves Its Own Work

## Short Description (< 200 chars)
Four generic BAND seats (planner, builder, independent reviewer, tester) built pocketful from a single human dispatch. Automated checks run in an isolated offline container.

## Long Description

### 1. The Band
The factory operates four specialized seats over the Band Agentic Mesh connected to an OpenCode headless adapter:
- **Foreman (zai-org/GLM-5.3-Flash):** Coordinates work intake, breaks stage specs into REQ-numbered handoffs, and ensures consensus before advancing.
- **Smith (zai-org/GLM-5.3-Flash):** Implements service code, Dockerfile, and RUN.md, committing atomically to the repository under `Smith <Smith@factory.invalid>`.
- **Inspector (MiniMaxAI/MiniMax-M2.5):** Independent reviewer from a different model family. Independently executes test suites in clean environments and issues pass/rejection verdicts mapping each REQ ID to reproduced command output.
- **Stresser (zai-org/GLM-5.3-Flash):** Adversarial tester probing edge conditions (concurrency, idempotency replays, state restore, conservation of funds).

### 2. Why the Mandates are Generic
All mandate files (`mandates/*.md`) are strictly task-agnostic standing operating procedures. They enforce:
- Zero track-specific endpoints, route names, status codes, or domain nouns (verified by mechanical AST and regex linting).
- Explicit handoff contracts and REQ-ID evidence mapping.
- Dark-factory protocol: auto-rejecting questions to prevent stalling or human steering.
The same band mandates can build completely different services simply by swapping the dispatch brief.

### 3. How It Catches and Recovers from Bad Work
Quality assurance is built into the workflow through independent reproduction and adversarial probing:
- The Inspector refuses to accept claimed outputs without running checks independently.
- When defects are detected, exact terminal error logs are returned to Smith with structured rejection messages.
- Smith applies revisions and re-submits until all stage suites and isolated checks pass.

### 4. Measured Results, Costs, and Limitations
- **Harness & Offline Verification:** All completed stages pass validation under isolated network mode (`--network none`, 2 vCPU, 2 GiB memory cap).
- **Autonomy:** Exactly 1 human message (the initial dispatch) in the room log.
- **Known Limitations:** Subject to upstream inference provider rate limits and context length constraints during heavy build output inspection.

## Tags
Band Agentic Mesh, OpenCode, Featherless, Autonomous Software Factory, Python, Docker
