# FactoryOps Hackathon 2026 Baseline

## Branch safety assessment

| Item | Observed value |
|---|---|
| Source repository | `RafalW3bCraft/factory` |
| Protected checkout inspected | `/mnt/hostname/arch-factory` on `main` |
| Protected checkout HEAD | `ecacc93b040fef6491c120b21bdb714d22efa041` |
| Refreshed `origin/main` baseline | `317108a2725024bec29c071fdef9eb623e7987fa` |
| `origin/hardening/prod-ready` | `446f270c95910f0ded5df96669ab579fc95cde52` |
| Event branch before creation | Absent locally and on `origin` |
| Event worktree | `/mnt/hostname/factoryops-flip-switch-2026` |
| Event branch | `flip-the-switch-2026` |
| Event branch base | `origin/main` at `317108a2725024bec29c071fdef9eb623e7987fa` |

The inspected protected checkout had no tracked modified or untracked files in
`git status --porcelain=v1`. Ignored files, including `.env`, were not read or
copied. No protected branch was switched, reset, rebased, or modified.

## Delivery record

| Milestone | SHA / evidence |
|---|---|
| Baseline commit | Pending this commit |
| RED test commit | Pending |
| GREEN implementation commit | Pending |
| Live Switch/Discord evidence | Pending interactive setup |
| Final event branch SHA | Pending release gate |

## Implementation boundary

FactoryOps is a separate Switch-native mode. The existing Band/OpenCode
runtime, its mandates, and its startup scripts remain a supported legacy mode
and are not rewritten by this work.
