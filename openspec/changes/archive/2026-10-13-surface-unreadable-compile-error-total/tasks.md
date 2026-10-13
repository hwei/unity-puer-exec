# Tasks

## 1. Distinguish an unreadable total

- [x] 1.1 Change `_read_compile_error_total` to return `None` when the response has no usable integer `total`, and verify with a focused test that a `not_available` / reset body yields `None` while a valid `{"total": N}` body yields `N`.
- [x] 1.2 Update `_stop_success_result` so a `None` read omits `compile_errors_total` and sets `compile_error_total_available: false`, keeps `no_compile_observed` at `0`, and guards the follow-up branch with `.get("compile_errors_total", 0) > 0`; verify with a command-layer `stop` test asserting the omitted field and the marker.
- [x] 1.3 Keep the successful `stop` path unchanged and verify the existing `stop` test that asserts a real `compile_errors_total` still passes.

## 2. Integration verification

- [x] 2.1 Run the default suite from `openspec/specs/validation-host-integration/how-to-run.md` and verify no regression.
- [x] 2.2 Run `openspec validate surface-unreadable-compile-error-total --strict` and `openspec validate --all`, and verify both pass.
- [x] 2.3 Complete the apply closeout review and record whether the change surfaced any new follow-up candidate.

## Workflow follow-up

- Archive the change after review requirements are satisfied.
- Verify the archived result.
