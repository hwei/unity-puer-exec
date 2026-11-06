# Proposal

## Why

The `play-mode-control` spec and `play --help` both promise that the forced
run-in-background override never modifies the project's Player Settings. The
four-follow-up closeout (archived in commit `c3f5bb9`) observed the opposite on
the real host: after a real-host run of `PlayModeCompileBlockRealHostTests`
ended and the Editor exited, the host's `ProjectSettings/ProjectSettings.asset`
held `runInBackground: 1`. The host was git-clean before the run. A user's
project should not pick up an unrequested settings diff because an agent ran
`play`.

## What Changes

- `play` keeps forcing `Application.runInBackground = true` by default, but sets
  it only while the Editor is already in play mode. Unity does not persist
  changes made during play mode to the project. The `/play-mode` handler today
  also sets the value in edit mode, just before entering play, and that write is
  removed.
- If the real host shows that a play-mode-only write still reaches the asset,
  for example when the Editor exits during play, a snapshot/restore of the
  project value is added as a fallback.
- The existing "Project settings stay unmodified" scenario is made precise: the
  check runs after the Editor has exited, because that is when Unity writes
  `ProjectSettings.asset`, and it covers the case where the Editor closes while
  still in play mode.
- `play --help` and the code comments stop claiming more than the
  implementation guarantees.
- A real-host regression asserts that `ProjectSettings.asset` is byte-identical
  before and after a forced play session that ends with the Editor exiting.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `play-mode-control`: the requirement "Play forces run-in-background by
  default" gets a precise, testable definition of "Player Settings are not
  modified". The check is done on disk after the Editor exits, and it also
  covers an Editor that exits during play.

## Impact

- Package: the `/play-mode` handler in `Editor/UnityPuerExecServer.cs`, where
  the edit-mode assignment is removed and the comments are corrected.
  `Editor/UnityPuerExecPlayMode.cs` changes only if the fallback is needed.
- CLI: help text in `cli/python/help_surface.py`. The result shape does not
  change.
- Tests: `tests/test_package_layout.py` (hook content assertions) and a new
  real-host case beside `PlayModeCompileBlockRealHostTests`.
- Validation hosts: real-host runs stop leaving a `ProjectSettings.asset` diff
  behind.
