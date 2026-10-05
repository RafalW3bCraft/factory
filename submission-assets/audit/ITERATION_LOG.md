# Iteration Log

## Iteration 1: Truth baseline (read-only)

### What I found
- The repo ground truth is in `docs/FACT_SHEET.md` and `room.json`.
- The authoritative room export has 683 messages with sender counts: Inspector 257, Smith 249, Foreman 95, Stresser 78, Metal 4.
- The human step count is 4 total: initial dispatch, re-dispatch after timeout, `continue` after a ~1h55m stall, and one steering note.
- The stage-1 final report and the timeline in the room are consistent with a roughly 44-minute dispatch-to-final window.
- The repo includes a real OpenCode timeout chain and one FATAL server crash, which must be disclosed rather than hidden.

### What I changed
- Created the read-only manifest baseline at `submission-assets/audit/manifest.before.sha256`.
- Added `submission-assets/audit/verify_facts.py` to compute the room facts directly from `room.json`.
- This work is deliberately limited to the allowed `submission-assets/` output area; no frozen repository files were edited.

### Evidence
- `room.json` message export confirms the sender split and the four human messages.
- Verified output from the script shows `total_messages = 683`, `human_message_count = 4`, and `timeout_count = 3`.
- The FATAL note is present in the room/exported evidence and the repository `events.log` file; it remains an honesty risk for the final submission.

### Risks / remaining
- Missing official harness package (`python -m harness ...`) means the repo cannot prove a fresh harness pass without the external dependency.
- The real Band Desktop room recording is still missing; it is a required artifact and cannot be fake-generated.
- `stage-1/RUN.md` contains a machine-specific personal path and must be treated as a human-review item, not a frozen edit target.

### Next iteration
- Move to document correction only in non-frozen files, with all changes tied to a message ID or direct command output.
- Then continue with the tooling audit and the slide/video package generation, keeping all evidence attached to room IDs and command results.
