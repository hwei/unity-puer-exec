## Why

`auto-dismiss-api-updater-dialog` shipped with unit coverage only. No automated case actually makes Unity show the ScriptUpdater consent dialog, so the real window shape, message text, `No` button labels, and click/confirm behavior are verified exclusively by mocks. A real-host regression in the Win32 recovery path (or a localized dialog message) would not be caught.

## What Changes

- Add a real-host integration case that makes the validation host Editor show the ScriptUpdater consent dialog, then asserts the CLI auto-declines it and reports `warning = "api_updater_declined"` on the command's normal status (never `modal_blocked`).
- Add a repository-owned host fixture that triggers the dialog: seed a source file whose code references an obsolete/`[UnityUpgradable]` API so ScriptUpdater prompts on import, and restore or remove it after the case.
- Require a diagnosed outcome: if the dialog cannot be triggered deterministically on the current host/Unity version, the case records the specific blocker and skips with that reason instead of passing vacuously.
- Capture the observed dialog message text when the host Editor is non-English so the fingerprint matcher can be extended in a follow-up without changing the warning contract.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `validation-host-integration`: require real-host coverage of the ScriptUpdater consent-dialog recovery path, including the trigger fixture and a diagnosed skip when the dialog cannot be produced.

## Impact

- `tests/test_real_host_integration.py`: new case and fixture helpers.
- A small host-asset seed/restore helper (obsolete-API source under the host project) that leaves the host clean after the run.
- The follow-up is validation-only; no product code change is expected unless the real dialog disproves the matcher or click path, in which case a separate product change is filed instead of loosening the test.
