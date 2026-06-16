# Host Validation Evidence

Real-host validation on Unity 2022.3.62f2 (Mono), validation host
`c3-client-tree2/Project`, 2026-06-16. Host wired via
`tools/prepare_validation_host.py` (`embedded_package_shadowing=false`,
dependency `file:../../../unity-puer-exec/packages/com.txcombo.unity-puer-exec`).

Gate: `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1`. Unity exe resolved at
`E:\Program Files\Unity\Hub\Editor\2022.3.62f2\Editor\Unity.exe`.

## Occupied-preferred-port rollover — PASS

`test_control_port_rolls_over_when_preferred_port_occupied_against_real_host`
passed against the live host:

```
test_control_port_rolls_over_when_preferred_port_occupied_against_real_host ... ok
```

The test cold-started the interactive Editor on the free preferred port 55231,
ran the retry-binder for 55231, forced a domain reload via
`exec UnityEditor.EditorUtility.RequestScriptReload()`, and the binder won 55231
in the `Stop()`→`Start()` window. It then observed a ready `/health` on a later
port (55232+, excluding 55231 which the binder held) with matching
`port` / `base_url` identity — a genuine rollover rather than a whole-scan
failure. The binder was released in teardown so the Editor reclaims 55231 on its
next reload.

## Batch-mode service suppression — PASS

`test_batch_mode_process_suppresses_control_service_against_real_host` passed
against the live host (run in isolation, see harness note below):

```
test_batch_mode_process_suppresses_control_service_against_real_host ... ok
Ran 1 test in 18.840s
OK
```

A one-shot `Unity.exe -batchMode -nographics -quit -projectPath <host>
-logFile <tmp>` process loaded the editor domain, fired `[InitializeOnLoad]`,
and its log contained `[UnityPuerExec] Skipping control service start in
batch-mode process` and neither `Ready on port` nor `Failed to bind any port` —
confirming the batch-mode guard suppresses the control listener.

## Harness note — pre-existing locale-dependent `is_pid_running` defect

Running both new cases in a single `unittest` invocation surfaced a pre-existing
defect unrelated to the port-binding behavior under test. The two tests pass
individually but the second test in a sequence fails in the inherited
`setUp` → `_ensure_clean_test_boundary`:

```
AssertionError: failed to establish a clean real-host boundary:
  {'ok': False, 'status': 'not_stopped', ... 'unity_pid': 104136,
   'diagnostics': {'unity_pids': [], 'taskkill_exit_code': 128, ...}}
```

Root cause: `unity_session_process.is_pid_running` (cli/python) checks `tasklist`
output only for the English sentinel `"No tasks are running"`. On a localized
(here: Chinese) Windows, `tasklist` emits a localized "no tasks" line, so the
check never matches and `is_pid_running` returns `True` for *any* PID, including
a dead one. After a test's teardown kills its Editor, the stale
`Temp/UnityPuerExec/session.json` still records the now-dead Editor PID; the next
test's clean-boundary check believes that dead PID is still running, runs
`taskkill` (which reports "process not found", exit 128), and reports
`not_stopped`. `list_unity_pids` is unaffected because it parses the CSV
`Unity.exe` rows rather than matching the English sentinel.

Impact is broader than these tests: any sequential real-host run on a non-English
Windows host hits this, which is why the full `tests.test_real_host_integration`
suite has only ever been validated test-by-test on this machine. This is logged
as a follow-up (tooling-improvement / validation-gap); it is out of scope for
this validation-only change, which makes no product/runtime code changes.
