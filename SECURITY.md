# Security Policy & Threat Model

## Reporting Security Vulnerabilities

We take security seriously. If you discover a vulnerability or potential exploit in the Dark Factory system, please report it privately:

- **Security Contact:** `thewhitefalcon13@proton.me`
- **Response Window:** Acknowledgement within 48 hours; assessment and mitigation within 7 business days.
- **Please Do Not:** Open public GitHub issues or public pull requests disclosing unpatched vulnerabilities.

---

## Threat Model & Security Architecture

Dark Factory operates multiple autonomous AI agents with tool execution capabilities. The architecture enforces multi-layered technical containment:

### 1. Prompt Injection & Untrusted Input Boundary (Finding S6)
- **Principle:** Repository content, source code files, commit histories, PR diffs, and issue descriptions are treated strictly as **DATA, NEVER INSTRUCTIONS**.
- Operating mandates explicitly instruct agents to ignore override instructions embedded in analyzed repositories or fuzzing targets.
- Handoff messages between seats are structured markdown contracts with verifiable requirement IDs (`REQ-*`, `SEC-*`).

### 2. Execution Sandboxing & Least Privilege (Finding S1)
- **Container Isolation:** In containerized deployments (`docker-compose.sandbox.yml` / `Dockerfile.sandbox`), seats execute as an unprivileged user (`UID 1000`, `factory`).
- **Mount Restriction:** Only the target result repository (`RESULT_REPO`) is mounted read-write (`rw`) to `/workspace`.
- **Host Protection:** The host filesystem, host `$HOME`, and root partitions are never mounted into seat containers.
- **Privilege Dropping:** All Linux capabilities are dropped (`cap_drop: [ALL]`), and privilege escalation is disabled (`no-new-privileges:true`).

### 3. Credential Isolation & Secret Hygiene (Finding S2)
- **Process Isolation:** The OpenCode server runs with a sanitized environment (`env -u FEATHERLESS_API_KEY`) so that child tool processes cannot inspect provider API keys from environment listings.
- **Per-Seat Token Injection:** Individual seat runners receive only their specific seat credentials via isolated process variables (`BAND_AGENT_ID`, `BAND_API_KEY`), preventing cross-seat token access.
- **Mandate Auditing:** The mandate linter (`lint_mandates.py`) continuously scans all seat mandates to block hardcoded API keys, bearer tokens, and private keys.

### 4. Network Boundaries & Egress Control (Finding S6)
- **Localhost Only:** The dynamic testing seat (@Stresser) is restricted to local service addresses (`127.0.0.1` / `localhost`). Scanning or attacking external IP ranges, host networks, or third-party domains is strictly prohibited.
- **Authenticated Server:** The OpenCode headless API enforces HTTP Basic Authentication via `OPENCODE_SERVER_PASSWORD` (Finding S5), preventing unauthorized local process execution.

---

## Safe Environment Parsing (Finding S3)

All factory shell scripts and Python runners parse `.env` files using deterministic KEY=VALUE parsers (`scripts/load_env.sh` and `factory.env`). Shell execution (`source .env` or `eval`) is strictly prohibited, neutralizing arbitrary command execution payloads embedded in environment files.
