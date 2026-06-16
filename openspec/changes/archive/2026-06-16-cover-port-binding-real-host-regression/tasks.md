## 1. Batch-mode skip regression (autonomous)

- [x] 1.1 Add a real-host helper that launches `Unity.exe -batchMode -nographics -quit -projectPath <host> -logFile <tmp>` and returns the captured log path/exit code, reusing the existing `_require_unity_editor` / project-path resolution.
- [x] 1.2 Add a test asserting the batch-mode log contains `Skipping control service start in batch-mode process` and contains neither `Ready on port` nor `Failed to bind any port`.
- [x] 1.3 Detect the host-project-already-open / lock condition and `skip` (not fail) with a machine-usable reason; document the "host project must not be open interactively" prerequisite in the test docstring.

## 2. Occupied-preferred-port rollover regression

- [x] 2.1 Add a retry-binder helper that continuously polls to bind the preferred control port (55231) from the test process and releases it deterministically in teardown; skip with a reason when 55231 is already held by an unrelated process at start.
- [x] 2.2 Add a forced-reload helper that triggers a domain reload via `exec` of `CS.UnityEditor.EditorUtility.RequestScriptReload()` (tolerating the expected post-reload disconnect), with a win32 `SetForegroundWindow` + touched-script fallback if the exec trigger proves unreliable.
- [x] 2.3 Add the test: start the retry-binder, force a reload so the binder wins 55231 in the `Stop()`→`Start()` window, then assert `/health` reports ready on a later port (55232+) with matching `port` / `base_url` identity; retry the reload once before failing if the Editor reclaimed 55231.

## 3. Spec, docs, and gating

- [x] 3.1 Confirm both tests reuse `_real_host_tests_enabled()` gating and skip cleanly when prerequisites are missing, keeping them outside the default unit-test workflow.
- [x] 3.2 Update `openspec/specs/validation-host-integration/how-to-run.md` with the batch-mode prerequisite and any operator-assisted rollover step.

## 4. Validate and closeout

- [x] 4.1 Run the default mocked/unit suite to confirm no regression and that the new tests skip when the real-host gate is off.
- [x] 4.2 Run the new cases against a real Unity/Mono host with the gate enabled and capture the transcript as evidence. (rollover PASS in sequence; batch-mode skip PASS in isolation — see `validation-evidence.md`. A pre-existing locale-dependent `is_pid_running` defect blocks a green two-test sequential run; logged as follow-up.)
- [x] 4.3 Update `meta.yaml` `updated_at`; run the apply closeout finding summary and recommend the `git commit` / `openspec archive` / final `git commit` sequence.
