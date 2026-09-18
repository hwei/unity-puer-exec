## Why

Every project-scoped `exec` and `wait-for-exec` brings the Unity Editor main window to the foreground via `SetForegroundWindow` before contacting the control service (`_bring_unity_to_foreground`, `cli/python/unity_puer_exec_runtime.py:2149`). During parallel work — several agents or sessions driving one or more Editors — this repeatedly steals focus from whatever the operator is doing, and it does so on every single request rather than only when it could matter.

The original justification no longer holds. The nudge was added so Unity would notice changed files, because at the time the only refresh path was a JS-side `AssetDatabase.Refresh()` that did not reliably trigger compilation without Editor focus. The server now performs a native `AssetDatabase.Refresh()` on the Editor main thread when `refresh_before_exec` is set (`UnityPuerExecServer.cs:615-633`, dispatched through `MainThreadActions` in `OnEditorUpdate`), so refresh and recompilation are triggered server-side with no focus dependency. What remains of the nudge is an implicit, undocumented trigger for Unity's focus-gated ambient auto-refresh — a side effect, not a contract — bought at the cost of a focus steal on every request.

## What Changes

- Remove the `_bring_unity_to_foreground(session)` calls in `run_exec` (`unity_puer_exec_runtime.py:1263`) and `run_wait_for_exec` (`unity_puer_exec_runtime.py:1463`).
- Remove `_bring_unity_to_foreground` (`unity_puer_exec_runtime.py:2149`) and the helper it delegates to, `unity_modal_blockers._foreground_unity_window` (`unity_modal_blockers.py:144`).
- Remove the test-side equivalent: `_nudge_editor_foreground_win32` (`tests/test_real_host_integration.py:326`) and its two call sites (`:403`, `:1156`). Its own docstring already states the server-side refresh path does not require focus.
- Leave Safe Mode dialog dismissal exactly as it is. `_click_via_keyboard` (`unity_modal_blockers.py:411`) calls `SetForegroundWindow` on the *dialog* hwnd so `keybd_event` has a delivery target; that dialog is rare and the focus cost is acceptable. No foreground-restore logic and no global opt-out switch are added — this change removes a per-request behavior, it does not build a focus-policy mechanism.

Behavior change to be aware of: after this change, a plain `exec` following a C# edit no longer has an implicit trigger for Unity's ambient auto-refresh. `exec --refresh-before-exec` is unaffected and remains the explicit path. Automating the on-demand case is tracked separately as `refresh-on-change`; until that lands, the contract is simply that the CLI does not implicitly refresh.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `compile-error-surface`: remove the requirement "CLI brings Unity to foreground on every exec" (and its two scenarios). This is a behavior removal, so the durable spec must stop asserting it; the remaining requirements in that spec are unaffected.

## Impact

- `cli/python/unity_puer_exec_runtime.py` — two call sites and the wrapper function.
- `cli/python/unity_modal_blockers.py` — `_foreground_unity_window`. Note `_get_unity_main_window_title` (`:176`) stays: Safe Mode detection reads the main window title and does not foreground anything.
- `tests/test_real_host_integration.py` — remove the nudge helper and both call sites; `_trigger_domain_reload_via_touched_script` continues to work through the server-side refresh path, and `RequestScriptReload` remains the primary reload trigger.
- `openspec/specs/compile-error-surface/spec.md` — one requirement removed.
- No C# change and no CLI surface change: no command, flag, status, or exit code is added or removed.
