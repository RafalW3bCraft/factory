# Video shot list

## Purpose
This is the production plan for the Pocketful Factory submission video. The
supplied files include real BAND Desktop room recordings; the cut uses actual
room footage and does not simulate or recreate the chat.

## Sequence

1. Opening — Pocketful Factory and the four-seat workflow.
2. Problem — balance conservation and safe malformed-request handling.
3. Workflow — Foreman, Smith, Inspector, and Stresser roles.
4. Real room excerpt — review request, Inspector acceptance, and hardening order.
5. Defect story — Stresser's C1 concern, Smith's C1 fix and C2 self-find.
6. Real room follow-up — Inspector accepts the delta and Stresser reports a clean verdict.
7. Verification — official 147/147 result and separate private 145/145 smoke suites.
8. Autonomy accounting — four human messages, three timeouts, and a roughly 1h55m stall.
9. Stage boundary — Stage 1 shipped; Stage 2 uncommitted; Stages 3 and 4 not reached.
10. Closing — scope and limitations.

## Redaction and source handling

- The video uses cropped portions of the supplied real BAND room captures.
- It excludes browser/account chrome and terminal/editor footage, which showed
  an API-key browser tab, account details, and local paths.
- The room footage is cropped to the conversation. Visible workstation paths
  are covered with opaque redaction bars.
- Original capture audio is not used. The narration is generated separately.
- Input files are left untouched; only the presentation export is sanitized.

## Export

`build_video.py` creates `pocketful-factory-video.mp4` as a 1920×1080 H.264
presentation with narration and masked room excerpts.
