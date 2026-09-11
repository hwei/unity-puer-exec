## Why

Unity's ScriptUpdater can show a Yes/No modal during C# compilation ("Some of this project's source files refer to API that has changed..."). The Editor main thread stays blocked until a human clicks, so unattended `wait-for-compile` / `exec --refresh-before-exec` / session boot never return. The CLI already auto-dismisses Safe Mode; this dialog is the same class of hang and is not in the catalog.

## What Changes

- Recognize the API Updater consent dialog by its **message body** (not title alone) and auto-click **No**. Never click Yes (that rewrites project source).
- While a command is waiting on Unity, dismiss the dialog as often as it reappears in the same cycle (Unity can prompt per compilation unit).
- After a dismiss, keep waiting for compile/session settle. Do not treat the click as completion.
- Any command that dismissed the dialog in that request attaches `warning: "api_updater_declined"` plus `warning_detail`. This is an extra field on the command's normal terminal status, not a replacement of `status: "warning"` used by async exec results.
- CLI-owned cold launch always passes `-disable-assembly-updater` (Unity docs: this only disables AssemblyUpdater for DLLs; ScriptUpdater and this dialog still run, so dialog-based warning detection still works). Do not treat the `[Assembly Updater] Ignoring assembly` log line as this warning — it would fire on every CLI launch.
- Agents never see this dialog as `modal_blocked`. Save-scene dialogs stay on the existing explicit-resolve path.

## Capabilities

### New Capabilities

- `api-updater-recovery`: Detect the ScriptUpdater consent dialog, auto-decline it, attach a machine-readable warning to the in-flight command, and inject `-disable-assembly-updater` on CLI-owned launches without losing that warning.

### Modified Capabilities

- `compile-wait`: `wait-for-compile` must poll for this dialog during appear and settle, auto-dismiss No, then continue the compile-edge wait; a settled cycle that dismissed the dialog still reports `compile_settled` and carries the warning.
- `formal-cli-contract`: `exec`, `wait-for-exec`, session-prep waits, `get-blocker-state`, and `resolve-blocker` treat this dialog as auto-recovered rather than `modal_blocked`; help/status text documents the warning field.
- `project-control-endpoint`: bound `compiling` health responses include `unity_pid` when known so `--base-url` waits can dismiss the dialog without a new endpoint.

## Impact

- `cli/python/unity_modal_blockers.py` catalog, matching (child Static text), and click path (BM_CLICK on No, not Enter).
- `cli/python/unity_puer_exec_runtime.py` wait-for-compile / exec blocker normalization / guidance.
- `cli/python/unity_session_wait.py` and launch in `unity_session_process.py`.
- Help surface and unit tests. Real-host coverage is optional and likely a follow-up: triggering the dialog needs a host with obsolete UnityUpgradable APIs.
- Windows-only dismiss, same as existing modal recovery. Non-Windows cannot click; the launch flag still applies on CLI-owned starts.
