# BAND Room Footage Checklist

## Supplied real footage

The supplied captures include real BAND room screens. The presentation uses
cropped excerpts of the review and hardening flow; it does not simulate or
recreate the chat.

## Events represented

- Inspector review request and acceptance.
- Foreman's hardening order to Stresser.
- The narration and captions cover Stresser's concern and Smith's fix; the room excerpt shows Inspector's later acceptance and Stresser's clean verdict.

## Privacy checks

- Crop out account/browser chrome, email or account identifiers, and terminal
  panes.
- Cover local workstation paths with opaque masks; do not use a translucent
  blur that leaves text readable.
- Mute source audio so spoken or notification content cannot leak.
- Rotate any credential that was actually exposed; redaction does not revoke it.

## Accuracy checks

- Describe the run as four human messages, three OpenCode timeouts, and an
  approximately 1h55m stall.
- Do not say Inspector rejected the first revision or found the cold-start
  defect. Stresser raised C1 after Inspector accepted the first revision;
  Smith self-found C2; Inspector accepted the revised delta.
