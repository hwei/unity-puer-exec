## 1. Dialog catalog

- [x] 1.1 Match the ScriptUpdater consent dialog by child message text (English fingerprint) and No/`&No` labels, using BM_CLICK rather than Enter, and verify a unit test identifies a fake dialog by message body not title
- [x] 1.2 Copy click_method and cancel labels through the supported-dialog listing so Safe Mode keyboard dismiss still works, and verify existing Safe Mode / save-scene tests still pass
- [x] 1.3 Add a bounded re-dismiss loop that clicks No until the window is gone or the wait budget expires, and verify a test with two sequential fake dialogs records two declines

## 2. Wait and exec recovery

- [x] 2.1 Poll and auto-decline during `wait-for-compile` appear and settle using session PID or compiling-health `unity_pid`, and verify a mocked compiling-stuck cycle becomes `compile_settled` with `warning = "api_updater_declined"`
- [x] 2.2 Poll and auto-decline during `wait_for_session` / project-scoped readiness, and verify a mocked boot wait continues after decline instead of stalling
- [x] 2.3 Auto-decline in exec / wait-for-exec blocker normalization instead of `modal_blocked`, attach the warning to the eventual primary status, and verify tests for completed, `unity_compile_error`, and running/timeout shapes
- [x] 2.4 Ensure `get-blocker-state` does not report this dialog as `modal_blocked`, and verify the existing save-scene `modal_blocked` tests still pass

## 3. Launch flag and compiling health

- [x] 3.1 Inject bare `-disable-assembly-updater` on CLI-owned cold launch, dedupe if already present, and do not add it to reserved switches; verify launch-arg tests cover inject, dedupe, and no usage error when the caller already passed it
- [x] 3.2 Include `unity_pid` on bound compiling `/health` JSON when known, and verify protocol/unit coverage that compiling payloads expose the pid
- [x] 3.3 Confirm `[Assembly Updater] Ignoring assembly` log lines do not set `api_updater_declined` by themselves, and verify a wait-for-compile test with that log and no dismiss omits the warning

## 4. Help and closeout

- [x] 4.1 Document auto-decline and `warning = "api_updater_declined"` on `wait-for-compile` and `exec` help / help-status, and verify the corresponding help tests
- [x] 4.2 Run the CLI unit suite (`python -m unittest discover -s tests -p "test_*.py"` excluding real-host if that is the repo convention) and record that all tasks above have tests or explicit out-of-scope notes
- [x] 4.3 Run `openspec validate auto-dismiss-api-updater-dialog --strict` and fix any schema issues so the change is archive-ready after apply
