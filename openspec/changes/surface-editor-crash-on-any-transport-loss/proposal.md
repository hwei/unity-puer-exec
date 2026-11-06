# Proposal

## Why

`editor-crash-surface` reports a crash only when an in-flight project-scoped
`exec` loses its connection as `not_available`. Two real crashes on 2026-11-06
(`stop-play-persisting-run-in-background` probe; crash reports
`Crash_2026-11-06_032837754` and `_033043638`) showed the gaps:

- **The crash arrived as `empty_response`.** The in-flight `exec` returned
  `empty_response` (exit 12), not `not_available`. `_is_not_available_response`
  does not match it, so the journal crash check never ran. The guidance then told
  the caller that the endpoint "may have dropped during a domain reload" and to
  retry.
- **Commands other than exec have no crash detection.** In `play`, `pause` and
  `stop`, `_post_play_mode` treats `empty_response` and `not_available` as a
  domain-reload edge. It re-resolves the endpoint and retries until the whole
  `--timeout-seconds` budget is used up, then reports a transport state. A game
  that crashes the Editor on entering play mode therefore costs the full timeout
  and is never reported as a crash. The compile-query commands have the same
  blind spot.

The maintainer has asked that unity-puer-exec detect Unity crashes, not just
transport failures.

## What Changes

- In-flight project-scoped `exec` runs its existing journal crash check on every
  transport loss: `empty_response` as well as `not_available`.
- Project-scoped commands that post to the control endpoint check the Editor
  process they were talking to, as named by the endpoint publication, before
  they retry, re-resolve, or give up on a transport loss. If that process exits
  within the existing crash grace window, the command stops at once and returns
  the existing terminal crash status `editor_crashed_during_request` (exit 26)
  with evidence: Editor pid, log path, and a crash report created after the
  command started. It does not wait out its budget, relaunch Unity, or retry.
  Affected commands: `play`, `pause`, `stop`, `wait-for-compile`,
  `get-compile-errors`, `get-compile-warnings`.
- Transport-loss guidance (`empty_response` / `not_available`) keeps the
  domain-reload explanation only while the Editor process is still alive.
- Help (`--help-status`) for each affected command lists the crash status.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `editor-crash-surface`: crash detection covers every transport loss of an
  in-flight exec, and extends to the other project-scoped control-endpoint
  commands.
- `play-mode-control`: the dropped-endpoint recovery requirement gains a carve-out.
  A drop caused by the Editor process exiting is a crash, not a reload edge to
  retry.

## Impact

- `cli/python/unity_puer_exec_runtime.py`:
  - the exec transport-loss branch;
  - `_post_play_mode` and the play-mode command loop;
  - the compile-query command paths;
  - a shared "did the published Editor exit?" helper.
- `cli/python/help_surface.py`: the crash status in the per-command status
  tables, and guidance that depends on whether the Editor is still alive.
- Tests: mocked CLI tests for each command and drop shape, plus one real-host
  case that crashes the Editor deliberately on entering play mode.
- Payload compatibility: callers that already branch on
  `editor_crashed_during_request` / exit 26 for `exec` get the same status from
  the other commands. Callers that relied on a crashed `play` timing out as
  `not_available` now get exit 26 sooner.
