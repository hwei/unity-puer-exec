# Status

## Current Focus

- `T1.4.1` is complete, but `0007` now needs a narrow follow-up revision on session discovery and Unity lifecycle semantics before `T1.4.2` starts.

## In Progress

- `T1.4.1.1` planning is in progress to revise the CLI contract around endpoint discovery, Unity launch responsibility, and the current `--keep-unity` assumption.

## Blocked

- No active blocker is currently recorded. The last host validation succeeded, but cold-start logs still contain host-local ShaderGraph import issues that remain outside the `unity-puer-exec` package boundary.

## Next

- Finish `T1.4.1.1` so `docs/decisions/0007-formal-cli-contract.md` reflects the intended session discovery and lifecycle model.
- Use `T1.4.2` to establish a product-owned CLI baseline that follows the revised `docs/decisions/0007-formal-cli-contract.md`.
- Use `T1.4.3` to formalize `--help`, stdout-first machine output, and transitional alias behavior on that baseline.
- Use `T1.5` to decide whether the final CLI should remain baseline-derived or ship as a more self-contained executable.
- Reuse `docs/decisions/0006-minimal-host-validation-proof.md` when the repo later needs a repeatable minimal host proof path.
