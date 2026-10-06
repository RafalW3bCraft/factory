# Hackathon Submission Form Copy

## Project Title
Pocketful Factory: A Four-Seat Software Factory With Independent Verification

## Short Description (< 200 chars)
Four BAND seats built and tested Pocketful Stage 1, using independent review, adversarial probes, and isolated verification.

## Long Description

### 1. The Band
The factory uses four specialized seats connected through BAND Desktop and an
OpenCode adapter:
- **Foreman:** Coordinates work, routes handoffs, and reports stage outcomes.
- **Smith:** Implements the service and commits revisions.
- **Inspector:** Independently checks the submitted revision and records an acceptance decision.
- **Stresser:** Probes edge cases including concurrency, idempotency, state restoration, and conservation of funds.

### 2. Generic Mandates
The four seat mandates describe reusable operating procedures rather than
Pocketful-specific product requirements. A mechanical lint check rejects
track-specific details in those mandates. A new task can use the same factory
by changing the dispatch.

### 3. Defect Discovery and Verification
Inspector accepted the first Stage 1 revision. After that, Stresser raised a
concern that an empty request body returned the wrong status. Foreman routed a
follow-up to Smith, who corrected that behavior and independently found a
cold-start index defect. Inspector then verified and accepted the revised
commit. The room evidence does not show an Inspector rejection causing either
fix.

### 4. Results and Limitations
- **Stage 1:** 147/147 official harness checks passed; independent review repeated the pass.
- **Additional checks:** Separate private smoke suites passed 145/145.
- **Autonomy accounting:** Four human messages were recorded: the original dispatch, a duplicate after a timeout, a continuation after a long stall, and a steering note. The run also had three OpenCode timeouts and an approximately 1 hour 55 minute stall.
- **Stage boundary:** Stage 1 shipped. Stage 2 was not committed to `main`; Stages 3 and 4 were not reached.
- **Limitations:** The factory depends on external BAND, OpenCode, and inference-provider services, and is subject to their availability and rate limits.

## Tags
Band Agentic Mesh, OpenCode, Featherless, Software Factory, Python, Docker
