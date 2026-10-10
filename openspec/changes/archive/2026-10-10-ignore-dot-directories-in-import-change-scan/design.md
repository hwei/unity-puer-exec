# Design

## Context

See proposal.md — Why. Inherited from `harden-real-host-per-case-reset`:

- `UnityPuerExecImportChangeTracker` watches `Assets` and `Packages` and treats `.cs`, `.asmdef`, `.asmref`, and `.rsp` as compile-triggering.
- `ExcludedSegments` already skips `/library/`, `/temp/`, `/logs/`, `/.git/`, and `/obj/`. A directory whose name starts with `.` is not skipped unless it is `.git`.
- Unity's asset pipeline ignores a folder whose name starts with `.`, so a script there is never compiled. `OnCompilationCompleted` therefore never clears that candidate.
- The real-host refresh cases plant probes in `Assets/__codex_validation_temp/.not_imported` for that reason. `test_change_made_before_install_is_caught_by_baseline_walk` and `test_play_mode_skips_refresh_and_preserves_pending_change` expect the tracker to see a `.cs` there.
- The reset harness deletes those probes before the next case. That workaround stays outside this change.

## Goals / Non-Goals

**Goals:**

- A compile-triggering file under a dot-directory does not mark the signal pending and does not start a refresh.
- A candidate already recorded under a dot-directory does not keep the signal pending.
- Tests that still need a file Unity will not compile, but the tracker must see, move to a folder Unity ignores for a different reason.

**Non-Goals:**

- Changing the CLI settle timeout or base-url `wait-for-exec` replay.
- Removing the harness delete of unimported probes.
- Ignoring every Unity special folder (trailing `~`, `cvs`, and the rest) in the tracker. A trailing-`~` folder remains visible to the tracker on purpose.

## Decisions

### D1. Skip dot-directories in the scan and in the candidate check

`IncrementalScan` does not enter a directory whose name starts with `.`, and it does not record that directory as a subdirectory. `IsExcludedPath` returns true when any path segment starts with `.`, so a candidate recorded before this rule still does not count as pending.

A file directly under `Assets` or `Packages` whose own name starts with `.` is not a directory segment. It stays in the scan. Unity may still ignore a file named `.Something.cs`; that case is not the one this change covers.

### D2. Move tracker-visible, Unity-invisible probes to a trailing-tilde folder

Unity also ignores a folder whose name ends with `~`. The baseline-walk and play-mode probes move from `.not_imported` to a sibling such as `not_imported~`. The tracker still walks it. A new case writes a `.cs` under `.not_imported` and asserts the signal stays `not_pending` and the next exec does not refresh.

### D3. Prove it on the real host

This repository has no C# unit host for the tracker. `RefreshOnChangeRealHostTests` is the proof. The default unit suite does not import the Editor assembly.

## Risks / Trade-offs

- A caller who intentionally put a script under a dot-directory to force a refresh will no longer get one. That script could not compile, so the old refresh could not finish.
- Leaving trailing-`~` folders visible keeps the existing isolation tests possible. It also means a `~` folder can still produce the same never-compile wait. That is accepted until a later change aligns the tracker with the rest of Unity's ignore rules.

## Migration Plan

No persisted protocol field changes. An Editor that already has a dot-directory candidate pending clears it on the next decision because the path is excluded, without waiting for a compilation.

## Open Questions

None.
