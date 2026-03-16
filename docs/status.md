# Status

Use this file only for current focus, blockers, and next steps. For workflow routing, start from `docs/index.md`.

## Current Focus

- `T2.7` is complete: the repository entry path now makes the plan-first rule explicit in `AGENTS.md`, `docs/index.md`, and `docs/workflow.md`, and `docs/workflow-closeout.md` now defines retroactive-plan recovery as an exception-only closeout path.

## In Progress

- No task is currently in progress.

## Blocked

- The last host validation succeeded, but cold-start logs still contain host-local ShaderGraph import issues that remain outside the `unity-puer-exec` package boundary.

## Next

- Use `T1.4.4` to implement the formal CLI help surface from `docs/decisions/0007-formal-cli-contract.md`.
- Use `T1.4.6` to add real validation-host CLI integration coverage instead of relying only on protocol-level tests.
- Use `T1.4.1.2` later to explore whether the CLI should adopt an explicit user-visible session identity model beyond the internal async continuation token/session-marker model.
- Use `T1.5` to decide whether the final CLI should remain baseline-derived or ship as a more self-contained executable.
- Reuse `docs/decisions/0006-minimal-host-validation-proof.md` when the repo later needs a repeatable minimal host proof path.
