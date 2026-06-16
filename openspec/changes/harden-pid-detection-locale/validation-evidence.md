# Validation Evidence

Chinese (non-English) Windows host, Unity 2022.3.62f2 (Mono), validation host
`c3-client-tree2/Project`, 2026-06-16.

## Unit: locale-independent liveness detection — PASS

Default mocked/unit suite after the fix: 257 tests OK (was 255; +2 new). The two
added cases in `tests/test_unity_session_modules.py`:

- `test_pid_present_in_tasklist_csv_is_locale_independent` — the parsing helper
  returns `True` only for a real PID-row CSV and `False` for an English "no tasks"
  line, a localized (Chinese) "no tasks" line, and empty output.
- `test_is_pid_running_handles_localized_no_match_output` — with a localized
  no-match `tasklist` output injected, `is_pid_running(<dead pid>)` returns
  `False` (the locale regression), and a PID-row output returns `True`.

## Real-host: sequential run is now green — PASS

Before this fix, running the two `cover-port-binding-real-host-regression` cases
in a single invocation failed: the second test died in the inherited
`setUp` → `_ensure_clean_test_boundary`, because `is_pid_running` reported the
prior test's already-killed Editor PID (recorded in a stale
`Temp/UnityPuerExec/session.json`) as still running on this Chinese Windows host.

After the fix, the same sequential invocation passes:

```
test_control_port_rolls_over_when_preferred_port_occupied_against_real_host ... ok
test_batch_mode_process_suppresses_control_service_against_real_host ... ok
Ran 2 tests in 86.209s
OK
```

The batch-mode test now clears the boundary check that previously failed,
confirming the stale dead-PID artifact is correctly read as not-running
regardless of the host's display language.
