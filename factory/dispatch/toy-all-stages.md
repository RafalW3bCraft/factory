You are the lead seat for our software factory. Build the stages of the toy
practice track listed below, sequentially, coordinating the other seats and keeping every stage
in its own complete, buildable folder.

Workspace root: {{WORK_ROOT}}
Working folder: {{HARNESS_REPO}}
Track: toy
Result repository: {{RESULT_REPO}}

Your goal is to implement each stage fully, and only then move to the next stage.

## Stage instructions

Work through the stages strictly in order; do NOT create stage-K/ until stage K-1
is accepted by @Inspector and probed by @Stresser. Copy-forward means: copy the
previous stage folder (never any .git directory inside it) and extend the copy.

<!--stage:1-->
### Stage 1
Read the full spec at: {{HARNESS_REPO}}/toy/spec/stage-1.md
Implement it in: {{RESULT_REPO}}/stage-1/
<!--/stage:1-->

<!--stage:2-->
### Stage 2
Copy stage-1/ to stage-2/ and extend it per: {{HARNESS_REPO}}/toy/spec/stage-2.md
<!--/stage:2-->

<!--stage:3-->
### Stage 3
Copy stage-2/ to stage-3/ and extend it per: {{HARNESS_REPO}}/toy/spec/stage-3.md
<!--/stage:3-->

<!--stage:4-->
### Stage 4
Copy stage-3/ to stage-4/ and extend it per: {{HARNESS_REPO}}/toy/spec/stage-4.md
<!--/stage:4-->

Each folder must contain a Dockerfile (listening on port 8080), a RUN.md (exact build/run commands) and the complete service source.
Do NOT copy or paste any content from the spec into mandates.

## Checks to run per stage (run from the toy-result/ repo)

```sh
# Activate harness venv first:
source {{HARNESS_REPO}}/.venv/bin/activate

python -m harness run --track toy \
  --repo {{RESULT_REPO}} \
  --stage 1 \
  --out {{CHECKS_DIR}}/toy-s1-$(date +%Y%m%d-%H%M%S)
```

Replace `--stage 1` with the stage number being checked.

A passing stage run prints `claimed stage: N`. The extra `fail` line for the
*next* stage's suite is expected and correct — a stage-1 folder should fail
suite 2.

@Smith: commit all changes to {{RESULT_REPO}} using:
  git -c user.name="Smith" -c user.email="Smith@factory.invalid" commit

@Inspector: run the checks yourself on the revision @Smith reports. Do not
accept without independently running them.

@Stresser: after @Inspector accepts, probe the running service for retry
safety, concurrent use and restart behaviour.

@Foreman: post the final report for each stage before dispatching the next
one. Include the revision hash, which checks passed, and any defects found
or fixed.
