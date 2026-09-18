## 1. Remove the foreground nudge from request paths

- [x] 1.1 Delete the `_bring_unity_to_foreground(session)` calls in `run_exec` (`:1263`) and `run_wait_for_exec` (`:1463`) in `cli/python/unity_puer_exec_runtime.py`; verify `grep -n "_bring_unity_to_foreground" cli/python/unity_puer_exec_runtime.py` matches only the definition.
- [x] 1.2 Delete `_bring_unity_to_foreground` (`cli/python/unity_puer_exec_runtime.py:2149`); verify no remaining import or reference of it anywhere under `cli/python`.
- [x] 1.3 Delete `_foreground_unity_window` in `cli/python/unity_modal_blockers.py:144`; verify `_get_unity_main_window_title` (`:176`) still exists and is unchanged, since Safe Mode detection reads the main window title without foregrounding it.

## 2. Remove the test-side nudge

- [x] 2.1 Delete `_nudge_editor_foreground_win32` (`tests/test_real_host_integration.py:326`) and both call sites (`:403` in `_trigger_domain_reload_via_touched_script`, `:1156` in the base-url refresh-before-exec test); verify `grep -n "nudge" tests/test_real_host_integration.py` returns nothing.
- [x] 2.2 Confirm the touched-script reload fallback still reaches a compile through the server-side refresh path; verify by running the real-host control-port rollover test with `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1` on a host machine and observing a compile edge rather than a hang.

## 3. Validate no focus-stealing path remains on request submission

- [x] 3.1 Grep every remaining `SetForegroundWindow` call site and confirm each is scoped to a dialog being dismissed, never to the Editor main window on the request path; verify the only remaining call is in `_click_via_keyboard` (`unity_modal_blockers.py:414-421`).
- [x] 3.2 Run the mock unit suite (`python -m unittest discover -s tests`) and verify it passes with no test depending on the removed functions.

## 4. Closeout

- [x] 4.1 Run `openspec validate --change stop-foreground-nudges --strict` and verify it reports no errors.
- [x] 4.2 Confirm the durable spec delta at `specs/compile-error-surface/spec.md` removes exactly the foreground requirement and touches no other requirement; then recommend `git commit`, `openspec archive stop-foreground-nudges`, and a final `git commit`.
