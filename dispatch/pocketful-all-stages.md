You are the lead seat for our software factory. Build all four stages of the
pocketful track sequentially, coordinating the other seats and keeping every
stage in its own complete, buildable folder.

Workspace root: /home/sp3ct0r/band-work
Working folder: /home/sp3ct0r/band-work/dark-factory-wearedevs
Track: pocketful
Result repository: /home/sp3ct0r/band-work/result

Your goal is to implement each stage fully, and only then move to the next stage.

## Stage instructions

For stage 1, read the full spec at:
/home/sp3ct0r/band-work/dark-factory-wearedevs/pocketful/spec/stage-1.md
Implement it in:
/home/sp3ct0r/band-work/result/stage-1/

When stage 1 is accepted by @Inspector and probed by @Stresser:
- Copy /home/sp3ct0r/band-work/result/stage-1/ to
  /home/sp3ct0r/band-work/result/stage-2/ (do NOT copy any .git directory
  inside the stage folder — delete it if it exists)
- Extend stage-2/ per the spec at:
  /home/sp3ct0r/band-work/dark-factory-wearedevs/pocketful/spec/stage-2.md

Continue the same copy-forward-and-extend pattern for stage 3:
/home/sp3ct0r/band-work/dark-factory-wearedevs/pocketful/spec/stage-3.md
→ /home/sp3ct0r/band-work/result/stage-3/

And stage 4:
/home/sp3ct0r/band-work/dark-factory-wearedevs/pocketful/spec/stage-4.md
→ /home/sp3ct0r/band-work/result/stage-4/

Each stage folder must contain exactly:
- Dockerfile (builds and runs the complete service listening on port 8080 with no external deps at
  runtime — all deps installed in the image)
- RUN.md (exact commands to build and start the service from a clean environment, e.g. docker build and docker run on port 8080)
- Complete service source (any language; judges do not import it)

Do NOT copy or paste any spec content into mandates.
Do NOT commit anything outside /home/sp3ct0r/band-work/result.
Do NOT create stage-3/ or stage-4/ until the earlier stage is accepted.

## Checks to run per stage

```sh
# Activate harness venv first:
source /home/sp3ct0r/band-work/dark-factory-wearedevs/.venv/bin/activate

# Replace N with the stage number being checked:
python -m harness run --track pocketful \
  --repo /home/sp3ct0r/band-work/result \
  --stage N \
  --out /home/sp3ct0r/band-work/checks/s${N}-$(date +%Y%m%d-%H%M%S)
```

A passing run prints `claimed stage: N`. The extra `fail` line for the next
stage's suite is expected — a stage-1 folder should fail suite 2. Read only
the `claimed stage:` line to judge completion.

For the final check of each stage, use `--mode isolated`:
```sh
python -m harness run --track pocketful \
  --repo /home/sp3ct0r/band-work/result \
  --stage N \
  --mode isolated \
  --out /home/sp3ct0r/band-work/checks/s${N}-isolated-$(date +%Y%m%d-%H%M%S)
```

Isolated mode has no outbound network. A service that quietly fetches
dependencies at runtime will fail in isolated mode. All runtime dependencies
must be bundled in the Docker image.

## Seat responsibilities

@Smith: implement one scoped work item at a time. Commit all changes to
/home/sp3ct0r/band-work/result using:
  git -c user.name="Smith" -c user.email="Smith@factory.invalid" commit

@Inspector: independently run the supplied checks on the revision @Smith
reports. Re-read the spec and test behaviours the checks do not exercise.
Accept only on reproduced evidence. Do not accept without running checks.
Do not edit product code.

@Stresser: after @Inspector accepts each stage, start the service from
stage-N/ and probe it: repeated identical requests, concurrent sends,
malformed input, and restart-with-populated-state. Report any defect with
the exact command and output. Do not edit product code.

@Foreman: before each stage's first handoff, ensure @Smith, @Inspector and
@Stresser are participants in this room. Post a final report for each stage
(revision hash, checks passed, defects found or fixed) before dispatching
the next stage dispatch.

## Critical business logic invariants (must never be violated)

1. **Conservation of Money**:
   - Total money across all wallets must always strictly equal the total seeded by `POST /_test/reset`.
   - Money moves only between wallets; never create, destroy, or leak funds.
   - No wallet balance may ever become negative, even transiently under concurrent requests.
2. **Exact Minor-Unit Integer Arithmetic**:
   - All amounts are exact integers representing minor currency units (e.g. cents). NEVER use floating-point numbers.
   - Equal splits follow the remainder rule: `base = amount // n; remainder = amount - base * n; shares = [base + (1 if i < remainder else 0) for i in range(n)]`.
3. **Idempotency & Replays**:
   - Idempotent write endpoints (`POST /payments`, `POST /requests/{id}/pay`, `POST /splits`, `POST /settlements`, `POST /authorizations`, `POST /payments/{id}/refunds`, `POST /correction-batches`) require the `Idempotency-Key` header.
   - Replaying the identical request returns `200 OK` with the exact original body and moves money at most once.
   - A different request body with the same key returns `409 idempotency_key_reuse`.
   - `POST /requests/{id}/decline` and `cancel` do NOT require idempotency keys.
4. **Feed Visibility**:
   - `GET /activity` returns payments only. A payment appears if and only if `visibility == "public"` OR the caller is the sender or receiver.
   - Requests are returned in `GET /requests`, never in the activity feed.
5. **Runtime & Port Contract**:
   - Listen on `0.0.0.0` using `PORT` environment variable (default `8080`).
   - `GET /health` must return `200 {"status": "ok"}` within 60 seconds of container start.
   - `POST /_test/reset` resets state to the fixture and returns `204 No Content`.
   - `GET /_test/export` (200 JSON) and `POST /_test/import` (204).

## Important: build to the specification, not to the tests

The harness ships only part of each stage's checks. The supplied checks are
signals for iteration, not a complete list of requirements. After the checks
pass, re-read the spec and ask what correct behaviour the checks never
exercise. Build to the specification.
