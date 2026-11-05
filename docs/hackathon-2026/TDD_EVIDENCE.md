# FactoryOps TDD Evidence

## Source and guarantees

The FactoryOps implementation was derived from the approved Track 01 plan.
The production guarantees are tested in `tests/test_factoryops.py`:

| Guarantee | Test coverage |
|---|---|
| Unsafe, repository-owned, root, relative, and non-empty demo paths are refused. | `test_create_demo_refuses_unsafe_roots` |
| A managed fixture has separate clean Builder, Inspector, and Stresser worktrees. | `test_create_demo_creates_isolated_fixture_worktrees` |
| A verifier receives the exact detached candidate SHA. | `test_prepare_verifier_checkout_detaches_at_the_candidate_commit` |
| Dirty verifiers and invalid role selection cannot replace evidence. | `test_prepare_verifier_checkout_rejects_dirty_worktree_and_unknown_role` |
| Approval must be linked, later than the request, and plainly affirmative. | `test_approval_record_requires_a_later_plain_language_affirmative_reply` |
| Completion requires matching Smith SHA, both independent passes, and approval. | `test_completion_requires_commit_both_independent_gates_and_approval` |
| The Switch room template uses four safe native Codex agents. | `test_template_uses_four_safe_native_codex_agents` |

## RED and GREEN record

- **RED:** `uv run pytest -q tests/test_factoryops.py` failed during collection
  because `factory.factoryops` did not yet exist. This occurred before
  production implementation and was committed as
  `test(factoryops): define governed workflow contract`.
- **GREEN:** after implementation, the same target passed: `7 passed, 5
  subtests passed`.
- **Suite:** `uv run pytest -q --cov=src --cov-fail-under=85` passed with `100
  passed, 5 subtests passed` and `91.34%` total coverage at the recorded run.

Live Switch/Discord evidence is intentionally separate in
`LIVE_DEMO_EVIDENCE.md`; it remains pending rather than being inferred from
unit or integration tests.
