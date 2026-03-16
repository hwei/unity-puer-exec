# Status

Use this file only for current focus, blockers, and next steps. For workflow routing, start from `docs/index.md`.

## Current Focus

- `T1.4.1.3` is complete: `docs/decisions/0007-formal-cli-contract.md` now defines token-driven async continuation for `exec` and `get-result`, and the next focus is resuming `T1.4.3` planning against that revised contract.

## In Progress

- No task is currently in progress.

## Blocked

- The last host validation succeeded, but cold-start logs still contain host-local ShaderGraph import issues that remain outside the `unity-puer-exec` package boundary.

## Next

- Write a new `T1.4.3` plan against the revised `0007` contract, including token-driven `get-result` behavior and the remaining non-help machine contract work.
- Use `T1.4.1.2` later to explore whether the CLI should adopt an explicit user-visible session identity model beyond the internal async continuation token/session-marker model.
- Use `T1.4.4` to implement the formal CLI help surface from `docs/decisions/0007-formal-cli-contract.md`.
- Use `T1.5` to decide whether the final CLI should remain baseline-derived or ship as a more self-contained executable.
- Reuse `docs/decisions/0006-minimal-host-validation-proof.md` when the repo later needs a repeatable minimal host proof path.
