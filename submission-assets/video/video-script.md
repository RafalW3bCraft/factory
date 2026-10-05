# Video script

## Intro
"Pocketful Factory is a four-seat autonomous software factory for the pocketful challenge. It turns a single dispatch into a reviewable, testable build without introducing hidden human steps."

## Problem
"The task is to protect a wallet and peer-to-peer payments system while preserving the balance ledger and handling the flow of funds exactly as specified."

## Room recording placeholder
"[HUMAN: RECORD BAND DESKTOP ROOM] This is the required Band Desktop room capture of the real room, including the dispatch, the review loop, and the final Stage 1 confirmation."

## Walkthrough
"The factory uses a Foreman, Smith, Inspector, and Stresser. It lints the mandates, launches the seats, and validates that the generated work is generic rather than track-specific."

## Stage 1 proof
"The shipped result is Stage 1: it builds cleanly, passes the isolated container checks, and returns a valid health signal. The proof commands include docker build, docker run with --network none --cpus=2 --memory=2048m, and the HTTP checks for /health and /_test/reset."

## C1 and C2 story
"Stresser noticed a concern about empty-body handling, and Smith then found an additional cold-start defect while verifying the fix. Inspector accepted the first revision, then accepted the deltaed revision after the fix. That is the real evidence chain in the room."

## Honesty and limits
"The room log contains four human messages, three OpenCode timeouts, and a ~1h55m stall. The project is honest about the limits: Stage 2 remained draft-only, and the actual BAND room recording is still pending human capture."

## Closing
"The repository is public, the Stage 1 result is proven, and the remaining human work is straightforward: record the Band room, fill the spend figure, and submit the final form before the deadline."
