# Status

Use this file only for current focus, blockers, and next steps. For workflow routing, start from `docs/index.md`.

## Current Focus

- `T1.4.2` is complete: the repo-owned Python CLI baseline now lives under `cli/python/`, and the next implementation focus is closing the remaining formal contract gaps under `T1.4.3`.

## In Progress

- No implementation task is currently in progress.

## Blocked

- No active blocker is currently recorded. The last host validation succeeded, but cold-start logs still contain host-local ShaderGraph import issues that remain outside the `unity-puer-exec` package boundary.

## Next

- Use `T1.4.1.2` later to explore whether the CLI should adopt explicit session identity beyond the current best-effort selector model.
- Use `T1.4.3` to fully implement the non-help portions of `docs/decisions/0007-formal-cli-contract.md` on the repo-owned baseline, including machine states such as `session_missing` and `session_stale`.
- Use `T1.4.4` to implement the formal CLI help surface from `docs/decisions/0007-formal-cli-contract.md`.
- Use `T1.5` to decide whether the final CLI should remain baseline-derived or ship as a more self-contained executable.
- Reuse `docs/decisions/0006-minimal-host-validation-proof.md` when the repo later needs a repeatable minimal host proof path.
