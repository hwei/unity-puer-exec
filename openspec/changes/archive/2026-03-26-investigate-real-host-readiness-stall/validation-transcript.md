# Real-Host Validation Transcript

## 2026-03-26: Focused reproducer for teardown-to-stall handoff

Environment:

- `UNITY_PROJECT_PATH=F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project`
- real-host tests enabled with `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1`

Focused sequence:

1. `wait-until-ready --project-path ... --unity-exe-path ... --include-diagnostics`
2. `exec --project-path ... --unity-exe-path ... --include-log-offset --code "export default function run(ctx) { return 1; }"`
3. `ensure-stopped --project-path ... --timeout-seconds 5 --include-diagnostics`
4. `wait-until-ready --project-path ... --unity-exe-path ... --ready-timeout-seconds 90 --activity-timeout-seconds 15 --include-diagnostics`

Observed results before code changes:

- Step 1 succeeded and launched Unity with `unity_pid=31000`.
- Step 2 failed immediately with usage error: `--include-log-offset has been removed; use log_range.start from exec response`.
- Step 3 returned `status=not_stopped` even though `taskkill_exit_code=0` and `taskkill_stdout` reported the Unity PID tree terminated.
- Step 4 failed with `status=unity_stalled`, `session.owner=project_recovery`, `unity_pids=[]`, `last_health_error=<urlopen error timed out>`, and `idle_seconds` just above the activity timeout.

Key diagnosis:

- The stale assertion path was still using removed CLI surface (`--include-log-offset` / `log_offset`).
- `ensure-stopped` could report `not_stopped` in the narrow window immediately after a successful `taskkill`.
- The next readiness attempt treated a fresh `Temp/UnityLockfile` as recovery-worthy even when no recoverable Unity process remained, which turned the handoff into `project_recovery -> unity_stalled` instead of a clean relaunch.

## 2026-03-26: Full suite split before code changes

Command:

- `python -m unittest tests.test_real_host_integration -v`

Observed split:

- Stale assertion failures:
  - `test_exec_log_offset_observation_chain_against_real_host`
  - `test_exec_rejects_promise_return_against_real_host`
- Genuine readiness instability:
  - `test_exec_rejects_legacy_fragment_script_against_real_host`
  - `test_exec_script_args_are_visible_against_real_host`
  - `test_resolve_blocker_cancels_modified_scene_prompt_against_real_host`
  - `test_wait_for_exec_reports_modified_scene_modal_blocker_against_real_host`

Isolation check:

- `test_exec_rejects_legacy_fragment_script_against_real_host` passed when run alone, confirming the stall was sequence-dependent rather than an isolated readiness failure.
