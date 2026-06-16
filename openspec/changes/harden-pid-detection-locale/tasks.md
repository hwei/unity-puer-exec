## 1. Locale-robust liveness detection

- [x] 1.1 Extract a pure helper (e.g. `_pid_present_in_tasklist_csv(output, pid)`) in `cli/python/unity_session_process.py` that parses `tasklist /FO CSV` output with `csv.reader` and returns whether a data row's PID column equals the queried PID, guarding `int()` parsing as `list_unity_pids` does.
- [x] 1.2 Rewrite `is_pid_running` to call `tasklist /FI "PID eq <pid>" /NH /FO CSV` and delegate the decision to the new helper, removing the English `"No tasks are running"` sentinel check.

## 2. Tests

- [x] 2.1 Add a unit test in the process-module suite asserting the helper returns `True` for a real PID-row CSV and `False` for both an English "no tasks" line and a localized (e.g. Chinese) "no tasks" line.
- [x] 2.2 Add a test that `is_pid_running` reports a non-running PID as not running by injecting a localized no-match `tasklist` output (monkeypatch `subprocess.run`), proving the locale regression is fixed without spawning processes.

## 3. Validate and closeout

- [x] 3.1 Run the default mocked/unit suite to confirm no regression and that the new tests pass.
- [x] 3.2 (Optional, host-gated) Re-run the two `cover-port-binding-real-host-regression` cases in a single `tests.test_real_host_integration` invocation on a non-English Windows host to confirm the sequential run is now green. (PASS: `Ran 2 tests in 86.209s OK` on c3-client-tree2; batch test now clears the inherited setUp that previously failed on the stale dead-PID artifact — see `validation-evidence.md`.)
- [x] 3.3 Update `meta.yaml` `updated_at`; run the apply closeout finding summary and recommend the `git commit` / `openspec archive` / final `git commit` sequence.
