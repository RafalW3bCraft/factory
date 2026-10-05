# Video shot list

## Purpose
This package is the production-ready submission scaffold for the final Pocketful Factory video. Because the real BAND Desktop room recording is not present in the current archive, every room-shot slot is explicitly marked for human capture and is not faked or simulated.

## Sequence
1. Cold open (10s): dark, minimal title card with repo and stage markers.
2. Problem statement (30s): wallet / P2P payments, risk of moving funds, need for conservation and validation.
3. BAND Desktop room recording slot (60-90s): [HUMAN: RECORD BAND DESKTOP ROOM] using the real room, focusing on the dispatch and final review flow.
4. Factory walkthrough (45s): start script, mandate linting, and the four-seat layout.
5. Stage 1 live proof (60s): docker build and isolated run; show `/health` and `/_test/reset`.
6. C1 / C2 story (60s): Stresser concern, Smith fix, Inspector delta-accept.
7. Honest autonomy ledger (45s): 4 human messages, 3 OpenCode timeouts, ~1h55m stall.
8. Close (15s): repo link and final requirement note; explicit “recording pending” text if the room clip is not yet captured.

## Room capture notes
- Use the actual Band room export associated with room ID `48bd09b2-3c1e-426c-9beb-29d79b6f8d91`.
- Prioritize the following timestamps from `room.json`:
  - 2026-10-05T09:15:48.169Z dispatch
  - 2026-10-05T09:33:22.587Z first timeout
  - 2026-10-05T09:40:41Z first verification pass
  - 2026-10-05T09:51:47Z Stresser concern
  - 2026-10-05T09:57:03Z fix commit
  - 2026-10-05T10:00:00Z final report
- Highlight the room action as a real conversation, not a synthetic diagram.

## Production requirement
The final `.mp4` must not be assembled until the room recording exists. Until that point, the project can ship the script, checklist, and slide deck, with the recording slot clearly flagged.
