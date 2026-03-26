## 1. Exec contract and runtime plumbing

- [x] 1.1 Extend the exec CLI surface to accept `--script-args`, parse it as JSON object input, and return explicit machine-readable failures for malformed or non-object values.
- [x] 1.2 Update direct exec payloads, pending exec artifact schema, and project-scoped replay so accepted requests preserve canonical script arguments across `wait-for-exec`.
- [x] 1.3 Update the Unity-side exec request and wrapper flow so scripts receive `ctx.args`, omitted args become `{}`, and request-id equivalence/conflict checks include canonical script arguments.

## 2. Help surface and repository tests

- [x] 2.1 Update published help, argument help, and relevant workflow examples to document `--script-args` and `ctx.args` without implying undocumented context fields or a second entry parameter.
- [x] 2.2 Add or update unit coverage for CLI validation, request replay, request-id conflict behavior, and pending-artifact persistence with script arguments.
- [x] 2.3 Add or update package/runtime coverage that asserts the exec wrapper exposes `ctx.args` and continues guarding the single-context module-entry contract.

## 3. Validation and closeout

- [x] 3.1 Run the repository unit suites that cover exec CLI/runtime behavior and confirm the new script-argument contract passes locally.
- [x] 3.2 If validation host prerequisites are available, run a real-host exec workflow that passes `--script-args` into a reusable script and verify the observed result matches `ctx.args`.
- [x] 3.3 Review the change for closeout readiness, including whether new follow-up work was identified and whether the change is ready for `git commit` and later `openspec archive`.

## Closeout status

- 2026-03-26: `investigate-real-host-readiness-stall` restored the real-host gate by removing the stale `--include-log-offset` assertions, hardening the stop/start test boundary, and avoiding false project recovery when only a fresh lockfile remains.
- Archive readiness for `add-exec-script-args` is now unblocked by the real-host suite; the follow-up gate that had deferred archive review is back to a trustworthy passing state.
