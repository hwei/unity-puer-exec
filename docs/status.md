# Status

## Current Focus

- `T1.2.2.2` is complete; the next major productization step is to establish a formal, product-owned CLI baseline under `T1.4`.

## In Progress

- `T1.4.1` planning is in progress to define the formal CLI contract before any baseline migration or packaging decision.

## Blocked

- No active blocker is currently recorded. The last host validation succeeded, but cold-start logs still contain host-local ShaderGraph import issues that remain outside the `unity-puer-exec` package boundary.

## Next

- Finish `T1.4.1` so the formal CLI contract covers command naming, parameter shape, output model, and workflow-oriented help guidance independently of packaging choices.
- Use `T1.4.2` and `T1.4.3` to establish a product-owned CLI baseline before deciding whether to keep adapting that baseline or replace it.
- Use `T1.5` to decide whether the final CLI should remain baseline-derived or ship as a more self-contained executable.
- Reuse `docs/decisions/0006-minimal-host-validation-proof.md` when the repo later needs a repeatable minimal host proof path.
