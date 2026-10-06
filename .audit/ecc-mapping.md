# ECC Component Mapping
*Generated: Phase 0 — discovery step (mandatory per plan §3)*

Install: `./install.sh --target antigravity --profile full` + `--profile python`
ECC version: v2.2.3

## Plan-need → installed component map
| Plan need | Expected ECC component | Installed? | Closest match |
|---|---|---|---|
| Planning, gate summaries | `planner` agent · `/plan` | ✅ | `.agents/workflows/feature-dev.md`, `gan-planner.md` |
| Python tooling review | `python-reviewer` / `code-reviewer` | ✅ | `.agents/agents/code-reviewer.md` |
| Shell review | `code-reviewer` + shellcheck | ✅ | code-reviewer.md; shellcheck is system tool |
| Secrets / supply chain | `security-reviewer` skill | ✅ | `.agents/rules/common-security.md` |
| Tests-first fixes | `tdd-guide` / `tdd-workflow` | ✅ | `.agents/skills/tdd-workflow/SKILL.md` |
| Dead code / duplicates | `refactor-cleaner` | ✅ | `.agents/agents/code-simplifier.md` |
| Docs | `doc-updater` | ✅ | `.agents/agents/doc-updater.md` |
| Quality gate | `verification-loop` skill | ✅ | `.agents/skills/verification-loop/SKILL.md` |
| Config audit / AgentShield | `/harness-audit` | ⚠️  | No harness-audit workflow found; use code-reviewer.md + security rules |

## Notes
- `factory/AGENTS.md` rule "Never execute start-factory.sh" is top-priority
  and overrides any ECC hook or workflow that would attempt external actions.
