# Status

## Current Focus

- `T1.2.2.2` is complete; the next major productization step is to establish a formal, product-owned CLI baseline under `T1.4`.

## In Progress

- No implementation task is currently in progress.

## Blocked

- No active blocker is currently recorded. The last host validation succeeded, but cold-start logs still contain host-local ShaderGraph import issues that remain outside the `unity-puer-exec` package boundary.

## Next

- Start `T1.4.1` to define the formal CLI contract and command tree independently of packaging choices.
- Use `T1.4.2` and `T1.4.3` to establish a product-owned CLI baseline before deciding whether to keep adapting that baseline or replace it.
- Use `T1.5` to decide whether the final CLI should remain baseline-derived or ship as a more self-contained executable.
- Reuse `docs/decisions/0006-minimal-host-validation-proof.md` when the repo later needs a repeatable minimal host proof path.
