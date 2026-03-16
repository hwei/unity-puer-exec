# Status

Use this file only for current focus, blockers, and next steps. For workflow routing, start from `docs/index.md`.

## Current Focus

- `T2.7` is complete: the repository entry path now makes the plan-first rule explicit in `AGENTS.md`, `docs/index.md`, and `docs/workflow.md`, and `docs/workflow-closeout.md` now defines retroactive-plan recovery as an exception-only closeout path.
- `T1.4.10` is complete: the misleading legacy direct-exec shell module/test names are gone, the retained shared transport layer now lives under `cli/python/direct_exec_client.py`, and formal CLI coverage remains centered on `unity_puer_exec.py`.

## In Progress

- No task is currently in progress.

## Blocked

- The last host validation succeeded, but cold-start logs still contain host-local ShaderGraph import issues that remain outside the `unity-puer-exec` package boundary.

## Next

- Use `T1.4.10` once the tool loop is complete enough to replace placeholder workflow snippets with runnable, empirically validated examples.
- Use `T1.4.5` to rewrite repository-facing docs so they point to `unity-puer-exec` help and `docs/decisions/0007-formal-cli-contract.md` instead of acting as the primary usage contract.
- Use `T1.4.6` to add real validation-host CLI integration coverage instead of relying only on protocol-level tests.
- Use `T1.4.1.2` later to explore whether the CLI should adopt an explicit user-visible session identity model beyond the internal async continuation token/session-marker model.
- Use `T1.5` to decide whether the final CLI should remain baseline-derived or ship as a more self-contained executable.
- Reuse `docs/decisions/0006-minimal-host-validation-proof.md` when the repo later needs a repeatable minimal host proof path.
