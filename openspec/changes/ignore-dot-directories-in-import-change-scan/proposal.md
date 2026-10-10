# Proposal

## Why

`harden-real-host-per-case-reset` found that `UnityPuerExecImportChangeTracker` treats a `.cs` inside a directory whose name starts with `.` as a compile-triggering change. Unity never imports those directories, so the signal stays `pending` and a later base-url exec waits for a compilation that cannot start. The reset harness now deletes those probes before the next case. The tracker should not count them in the first place.

## What Changes

- Stop treating compile-triggering files under a dot-directory as pending changes.
- Skip those directories while scanning, and ignore any candidate path that already points into one.
- Move real-host probes that must stay invisible to Unity but visible to the tracker out of dot-directories and into a directory Unity ignores for a different reason.
- Add a real-host case that a `.cs` written under a dot-directory does not mark the change signal pending and does not refresh.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `import-change-refresh`: a compile-triggering extension under a dot-directory is not a detected change.

## Impact

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecImportChangeTracker.cs`
- `tests/test_real_host_integration.py` refresh cases that currently plant probes under `Assets/__codex_validation_temp/.not_imported`
- No CLI contract change. The harness delete of those probes can stay.
