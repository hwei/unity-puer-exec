# Tasks

## 1. Remove the dead helper

- [x] 1.1 Delete `_invoke_reset_jsenv` from `cli/python/unity_puer_exec_runtime.py` and verify: `grep -rn "_invoke_reset_jsenv" cli/ tests/` returns no matches and `python -m py_compile cli/python/unity_puer_exec_runtime.py` succeeds.
- [x] 1.2 Run the default suite from `openspec/specs/validation-host-integration/how-to-run.md` and verify it passes with no regression.

## 2. Closeout

- [x] 2.1 Run `openspec validate remove-dead-reset-jsenv-invoker --strict` and `openspec validate --all`, and verify both pass.
- [x] 2.2 Complete the apply closeout review and record whether the removal surfaced any new follow-up candidate. Closeout finding: No new follow-up work identified. The removal was a self-contained deletion of an unreachable private helper; the default suite (655 tests) and both validations pass, and no new product, workflow, tooling, or validation-gap candidate surfaced.

## Workflow follow-up

- Archive the change after review requirements are satisfied.
- Verify the archived result.
