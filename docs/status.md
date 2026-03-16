# Status

Use this file only for current focus, blockers, and next steps. For workflow routing, start from `docs/index.md`.

## Current Focus

- `T1.4.1.1` is complete, and the revised CLI contract now records the selector model, `wait-until-ready`, `get-log-source`, and `ensure-stopped` as governance-level guidance for the implementation baseline.

## In Progress

- No implementation task is currently in progress.

## Blocked

- No active blocker is currently recorded. The last host validation succeeded, but cold-start logs still contain host-local ShaderGraph import issues that remain outside the `unity-puer-exec` package boundary.

## Next

- Use `T1.4.1.2` later to explore whether the CLI should adopt explicit session identity beyond the current best-effort selector model.
- Use `T1.4.2` to establish a product-owned CLI baseline that follows the revised `docs/decisions/0007-formal-cli-contract.md`.
- Use `T1.4.3` to formalize `--help`, stdout-first machine output, and transitional alias behavior on that baseline.
- Use `T1.5` to decide whether the final CLI should remain baseline-derived or ship as a more self-contained executable.
- Reuse `docs/decisions/0006-minimal-host-validation-proof.md` when the repo later needs a repeatable minimal host proof path.
