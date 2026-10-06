# Dark Factory — Operator Runbook

This runbook provides step-by-step instructions for operating, monitoring,
troubleshooting, and verifying autonomous runs with the Dark Factory.

---

## 1. Environment Preparation

### Paths and Directory Layout
All commands should be executed from the factory directory (`/home/sp3ct0r/factory`):

```bash
cd /home/sp3ct0r/factory
```

### Environment Variables (.env)
Ensure `.env` exists with strict `600` permissions:

```bash
cp -n .env.example .env
chmod 600 .env
```

Required keys in `.env`:
- `FEATHERLESS_API_KEY`: API key for Featherless AI.
- `RESULT_REPO`: Absolute path to the git workspace where agents implement code.

---

## 2. Band Seat Configuration

Create `agent_config.yaml` with permissions `600`:

```bash
cp -n agent_config.example.yaml agent_config.yaml
chmod 600 agent_config.yaml
```

Populate the four seat credentials generated in Band Desktop:
- `foreman`
- `smith`
- `inspector`
- `stresser`

---

## 3. Pre-Flight Verification

Before launching any mission, run the automated diagnostic check:

```bash
./preflight.sh
```

Ensure all items pass:
- [OK] git, uv, opencode, band CLI
- [OK] Virtualenv Python and dependencies
- [OK] Featherless API authentication (HTTP 200)
- [OK] Agent mandates validation
- [OK] Target workspace git repository
- [OK] Automated test suite (pytest)

---

## 4. Mission Execution Flow

### Step A: Initialize or Clean Workspace
```bash
# If creating a fresh workspace:
./bootstrap-repo.sh /home/sp3ct0r/factory/workspace

# Or point to an existing project:
export RESULT_REPO=/home/sp3ct0r/factory/workspace
```

### Step B: Render Mission Brief
Select the mission profile matching your goal:

```bash
# Profile 1: Full-Stack Engineering & Feature Implementation
./render-dispatch.sh engineering --task "Implement OAuth2 authentication service with refresh token rotation"

# Profile 2: Cybersecurity Audit & Hardening (OWASP / SAST / DAST)
./render-dispatch.sh security    --task "Audit backend API endpoints against OWASP Top 10 and apply fixes"

# Profile 3: Crash Isolation & Digital Forensics
./render-dispatch.sh forensics   --task "Reproduce intermittent race condition in event processor and fix"
```

The rendered text will be displayed in terminal and automatically copied to your clipboard (if `wl-copy` or `xclip` is installed).

### Step C: Start the Factory Supervisor
```bash
RESULT_REPO=/home/sp3ct0r/factory/workspace ./start-factory.sh
```

`start-factory.sh` will:
1. Verify mandates and models.
2. Spin up the local OpenCode server on port `4096`.
3. Launch child `run_seat.py` processes for Foreman, Smith, Inspector, and Stresser.
4. Execute a 15-second survival health check on all seats.
5. Enter watchdog mode with automated restart recovery.

### Step D: Dispatch to Lead Room
1. In Band Desktop, open the room with `@Foreman`.
2. Paste the rendered dispatch message.
3. Observe autonomous coordination:
   - Foreman adds Smith, Inspector, and Stresser to the room.
   - Foreman plans tasks, extracts requirements, and performs threat modeling.
   - Smith commits code in the workspace repository.
   - Inspector checks out revisions and conducts static analysis and security audit.
   - Stresser probes endpoints with fuzzing, concurrency stress, and resilience tests.
   - Foreman delivers the verified final report.

### Step E: Stop Factory
Once the run is complete:

```bash
./stop-factory.sh
```

---

## 5. Post-Mission Analysis & Auditing

Export the room history as `room.json` from Band Desktop, then analyze:

```bash
python3 src/analyze_room.py room.json --repo /home/sp3ct0r/factory/workspace
```

This generates:
- Active run duration and message counts.
- Mention interaction flow between seats.
- Defect and vulnerability catches (by Inspector and Stresser).
- Commit counts and file-touch activity per author.

---

## 6. Troubleshooting & Diagnostics

| Symptom | Root Cause | Solution |
|---|---|---|
| `FEATHERLESS_API_KEY is empty` | Missing key in `.env` | Add key to `/home/sp3ct0r/factory/.env` |
| `agent_config.yaml missing` | Missing seat config | Copy `agent_config.example.yaml` to `agent_config.yaml` and add credentials |
| `opencode did not become ready in 30s` | Port 4096 conflict or opencode error | Run `./stop-factory.sh` to kill orphaned processes, inspect `logs/opencode.log` |
| `seat 'X' died during startup` | Model mismatch or invalid API key | Check `logs/<seat>.log` for stack trace; ensure model is supported by provider |
| `Stale git lock detected` | Prior git operation crashed | Remove `.git/index.lock` in the target result repo |
| `RESULT_REPO is not a git repository` | Uninitialized target folder | Run `./bootstrap-repo.sh <path>` first |
