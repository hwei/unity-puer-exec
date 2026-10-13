# Tasks

## 1. Remove the dead helper

- [ ] 1.1 Delete `_invoke_reset_jsenv` from `cli/python/unity_puer_exec_runtime.py` and verify: `grep -rn "_invoke_reset_jsenv" cli/ tests/` returns no matches and `python -m py_compile cli/python/unity_puer_exec_runtime.py` succeeds.
- [ ] 1.2 Run the default suite from `openspec/specs/validation-host-integration/how-to-run.md` and verify it passes with no regression.

## 2. Closeout

- [ ] 2.1 Run `openspec validate remove-dead-reset-jsenv-invoker --strict` and `openspec validate --all`, and verify both pass.
- [ ] 2.2 Complete the apply closeout review and record whether the removal surfaced any new follow-up candidate.

## Workflow follow-up

- Archive the change after review requirements are satisfied.
- Verify the archived result.
