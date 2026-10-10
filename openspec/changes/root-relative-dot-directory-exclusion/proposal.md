# Proposal

## Why

`ignore-dot-directories-in-import-change-scan` made a compile-triggering file under a
directory whose name starts with `.` not count as a detected change. The tracker
applies that rule to every segment of the **absolute** normalized path. If the
validation host's project path itself contains such a segment — for example
`F:\.work\proj\Assets\Scripts\Thing.cs` — then every watched file carries it and the
tracker would treat the whole project as excluded, silently disabling automatic
refresh. Unity's asset pipeline only ignores dot-directories inside the `Assets/` and
`Packages/` roots it scans, not directories above the project root.

## What Changes

- Evaluate the dot-directory rule on path segments **relative to the watched root**
  (`Assets/` or `Packages/`), not on the absolute path prefix.
- Leave the existing fixed-segment exclusions (`library`, `temp`, `logs`, `.git`,
  `obj`) and the rest of the scan/decision behavior unchanged.
- Add coverage that a dot segment above the watched root does not suppress change
  detection.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `import-change-refresh`: the dot-directory exclusion is scoped to directory segments
  inside the watched `Assets/` or `Packages/` tree, so a dot segment in the project's
  own absolute prefix does not suppress detection.

## Impact

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecImportChangeTracker.cs`
- `tests/test_refresh_change_signal.py`
- No CLI contract change.
