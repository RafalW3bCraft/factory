You are the lead seat for our software factory. Build all four stages of the toy
practice track sequentially, coordinating the other seats and keeping every stage
in its own complete, buildable folder.

Workspace root: /home/sp3ct0r/band-work
Working folder: /home/sp3ct0r/band-work/dark-factory-wearedevs
Track: toy
Result repository: /home/sp3ct0r/band-work/toy-result

Your goal is to implement each stage fully, and only then move to the next stage.

## Stage instructions

For stage 1, read the full spec at:
/home/sp3ct0r/band-work/dark-factory-wearedevs/toy/spec/stage-1.md
Implement it in:
/home/sp3ct0r/band-work/toy-result/stage-1/

When stage 1 is accepted by @Inspector and probed by @Stresser, copy stage-1/
to stage-2/ and extend it per the stage-2 spec at:
/home/sp3ct0r/band-work/dark-factory-wearedevs/toy/spec/stage-2.md

Continue the same way for stage 3:
/home/sp3ct0r/band-work/dark-factory-wearedevs/toy/spec/stage-3.md
→ /home/sp3ct0r/band-work/toy-result/stage-3/

And stage 4:
/home/sp3ct0r/band-work/dark-factory-wearedevs/toy/spec/stage-4.md
→ /home/sp3ct0r/band-work/toy-result/stage-4/

Each folder must contain a Dockerfile (listening on port 8080), a RUN.md (exact build/run commands) and the complete service source.
Do NOT copy or paste any content from the spec into mandates.

## Checks to run per stage (run from the toy-result/ repo)

```sh
# Activate harness venv first:
source /home/sp3ct0r/band-work/dark-factory-wearedevs/.venv/bin/activate

python -m harness run --track toy \
  --repo /home/sp3ct0r/band-work/toy-result \
  --stage 1 \
  --out /home/sp3ct0r/band-work/checks/toy-s1-$(date +%Y%m%d-%H%M%S)
```

Replace `--stage 1` with the stage number being checked.

A passing stage run prints `claimed stage: N`. The extra `fail` line for the
*next* stage's suite is expected and correct — a stage-1 folder should fail
suite 2.

@Smith: commit all changes to /home/sp3ct0r/band-work/toy-result using:
  git -c user.name="Smith" -c user.email="Smith@factory.invalid" commit

@Inspector: run the checks yourself on the revision @Smith reports. Do not
accept without independently running them.

@Stresser: after @Inspector accepts, probe the running service for retry
safety, concurrent use and restart behaviour.

@Foreman: post the final report for each stage before dispatching the next
one. Include the revision hash, which checks passed, and any defects found
or fixed.
