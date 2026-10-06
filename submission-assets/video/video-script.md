# Pocketful Factory — Presentation Script

The final video uses the narration below with on-screen chapter captions. It
includes two real BAND room excerpts from the supplied recordings. The excerpt
is cropped to the conversation, workstation paths are masked, and the original
screen-recording audio is muted.

1. **Opening:** Pocketful Factory is a four-seat software factory built for a wallet and peer-to-peer payments challenge.
2. **Problem:** For payments, correctness means more than a successful response. Balances must conserve funds, and malformed requests must fail safely.
3. **Workflow:** Foreman coordinates, Smith implements, Inspector independently verifies, and Stresser probes resilience. Defects return to Smith for a verified follow-up.
4. **Real room excerpt:** This real Band room excerpt shows the review request, Inspector's acceptance, then a hardening order to Stresser. Workstation paths are masked.
5. **Defect story:** After that acceptance, Stresser flagged empty-body handling. Smith fixed it and independently found a cold-start index defect; Inspector accepted the delta.
6. **Proof:** Stage One passed 147 of 147 official checks. An independent review repeated the pass; separate private smoke suites passed 145 of 145.
7. **Autonomy accounting:** The run needed four human messages, included three OpenCode timeouts, and stalled for about one hour and fifty-five minutes.
8. **Stage boundary:** Stage One shipped. Stage Two was not committed to main; Stages Three and Four were not reached. This is the verified boundary of the result.
9. **Closing:** Pocketful Factory shows how handoffs, adversarial tests, and independent review can catch defects, while its record stays honest about human input.

The narration is generated text-to-speech. The ending card identifies the
voiceover as synthetic.
