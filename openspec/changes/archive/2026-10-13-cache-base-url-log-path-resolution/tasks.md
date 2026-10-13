## 1. Confirm the repeated probe

- [ ] 1.1 Confirm a single base-url observation command resolves its log path more than once, so `/health` is probed repeatedly for the same answer. Verify: count `probe_health_payload` calls for one `run_cli` invocation with a mocked payload.

## 2. Cache per invocation

- [ ] 2.1 Memoize the resolved base-url log path (including a resolved `None`) per invocation and have `_resolve_log_path` reuse it. Verify: one base-url command probes `/health` once for log resolution, and the selected path is unchanged.

## 3. Validation and Closeout

- [ ] 3.1 Add regression coverage: a base-url command that resolves the path more than once probes `/health` once; the selected path and the fallback to the platform default are unchanged; project-path behavior is unchanged. Verify: the probe-count assertion fails without 2.1.
- [ ] 3.2 Run `tests.test_unity_session_cli`, `tests.test_unity_session_modules`, and `tests.test_openspec_spec_hygiene`, then the full `tests/` suite. Verify: green, no behavioral change.
- [ ] 3.3 Run `openspec validate cache-base-url-log-path-resolution --strict` and `openspec validate --all`. Verify: clean.
- [ ] 3.4 Complete the required apply closeout review and record the finding with allowed categories.
