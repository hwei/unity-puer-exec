# Design

## Context

See proposal.md — Why. The tracker's `IsExcludedPath` has two exclusion inputs: a
fixed substring list (`library`, `temp`, `logs`, `.git`, `obj`) and, since
`ignore-dot-directories-in-import-change-scan`, a per-segment dot-prefix test over the
normalized absolute path. The scan starts at the watched roots returned by
`GetWatchedRoots()` (`Application.dataPath` and its sibling `Packages`), so every path
it tests is an absolute path that includes the project's own directory prefix.

The dot test is the only exclusion that is *positional*: Unity only ignores
dot-directories inside the `Assets/` and `Packages/` trees it imports, not directories
above them. The fixed substrings are project-independent names and do not have this
property.

## Goals / Non-Goals

**Goals:**

- The dot-directory rule applies only to segments inside the watched root.
- The fix stays in the pure `System.IO` path helpers so off-thread callers (today the
  watcher callbacks) keep their no-Unity-API guarantee.

**Non-Goals:**

- Reworking the fixed `ExcludedSegments` matching.
- Aligning the tracker with every Unity ignore rule (trailing `~`, `cvs`, and the
  rest); that remains the accepted limitation from the upstream change.

## Decisions

### D1. Scope the dot test to the path below the watched root

`GetWatchedRoots()` already enumerates the roots. Cache the normalized roots in plain
state when the tracker is installed, and have the exclusion helper strip the matching
root prefix before it splits segments and applies the dot test. A path that matches no
known root keeps the current behavior (test the full path), so an unknown input is
never silently trusted more than today.

Alternative considered: match the dot test only on each entry's own file name while
scanning. That fixes directories but not already-recorded candidate paths or watcher
events, which are also absolute — the same bug would survive in those paths.

Alternative considered: check segments after the first `Assets/` or `Packages/`
literal in the path. Rejected as brittle: a project could contain a nested directory
with that name, and the watcher roots are already known exactly.

### D2. Cache the roots without a Unity API on the callback path

`StartWatchersLocked` runs on the main thread and already computes the roots. Store
their normalized forms in a single field that the exclusion helper reads. The field is
published by reference replacement (a new immutable list replacing the old one), so a
concurrent reader sees either the previous complete list or the next one, never a
torn one; no lock is needed on the callback path. This keeps `IsExcludedPath` free of
`Application.` / `UnityEditor` tokens, which the source-invariant test asserts.

The cache belongs to tracker install, not to the watcher. When
`scan-only-import-change-signal` deletes `StartWatchersLocked`, the root cache moves
with root enumeration into `Install()`; the field and its publication contract stay
unchanged.

### D3. Prove it with a source invariant plus the existing real-host class

The tracker has no C# unit host. A source-level test can assert the helper consults the
cached roots and does not test the full path when a root matches. The real-host
`RefreshOnChangeRealHostTests` dot-directory case already pins the ordinary behavior;
the pathological absolute-prefix case needs a project relocation the suite cannot
stage, so it stays a source-level contract.

## Risks / Trade-offs

- If the cached root list is empty (tracker install failed before any root was
  recorded), the helper falls back to testing the full path — today's behavior, not a
  new failure mode.
- A root prefix that is not normalized identically to the candidate path would not
  match and would fall back to full-path testing. Both sides go through
  `NormalizePath`, so this is a consistency requirement on the cache, not a new risk.
