## 1. Fake-user32 test harness

- [ ] 1.1 Add a ctypes-shaped fake-user32 harness module under `tests/` that scripts window trees (handle, title, class name, style, visibility, enabled state, owner handle) and child controls (class name, style, text, control id); verify a smoke test constructs a tree and reads it back.
- [ ] 1.2 Expose in the harness the specific calls the new code needs: `GetWindow`/`GW_OWNER`, `IsWindowEnabled`, `GetWindowLong`/style, `GetWindowRect`, `EnumChildWindows`, `GetClassName`, `GetDlgCtrlID`, `SendMessage`, `PostMessage`; verify each returns the scripted value for a known handle.
- [ ] 1.3 Verify the existing mock unit suite still passes unchanged (`python -m unittest discover -s tests`), confirming the harness is additive.

## 2. Modal discrimination

- [ ] 2.1 Add owner-disabled discrimination in `cli/python/unity_modal_blockers.py`: a window with an owner (`GetWindow(hwnd, GW_OWNER)`) that is not enabled (`IsWindowEnabled`) is a true modal; verify with a harness tree where the owner is disabled and one where it is enabled.
- [ ] 2.2 Add the ownerless fallback: dialog style plus a size consistent with a modal prompt; verify a scripted ownerless dialog is classified modal and a scripted large ownerless window is not.
- [ ] 2.3 Verify the downgrade rule: a window failing both tests — including `Preferences`, `Project Settings`, `Build Settings`, `About Unity` stand-ins — is treated as non-blocking and never promoted to a blocker.

## 3. Unknown dialog detection and reporting

- [ ] 3.1 Replace the allowlist drop at `_match_dialog_spec` (`:175`) so a modal window with no catalog spec is reported as `type = "unknown_modal_dialog"` instead of discarded; verify a non-matching modal window now appears in `list_supported_modal_blockers` output.
- [ ] 3.2 Keep catalog behavior intact: a title hit still reports its stable type without modal discrimination, and an api_updater body match is still skipped as a blocker; verify both with harness trees.
- [ ] 3.3 Extend the blocker payload with `hwnd`, `title`, `body`, and `buttons` for unknown dialogs; verify no `known` and no `default_button` field is present in any payload.
- [ ] 3.4 Order multiple blockers so `unknown_modal_dialog` sorts ahead of catalog types; verify with a tree containing both an unknown and a save-scene dialog.
- [ ] 3.5 Confirm exec normalization never auto-dismisses an unknown dialog: `_normalize_exec_blocker_result` (`unity_puer_exec_runtime.py:2148`) must still return `modal_blocked` with `EXIT_MODAL_BLOCKED` and `scope = "exec"`; verify by unit test.

## 4. Button enumeration

- [ ] 4.1 Add `_enumerate_buttons(dialog_hwnd)` returning `{hwnd, label, ctrl_id}`; verify against a scripted dialog with two push buttons.
- [ ] 4.2 Exclude non-clickable controls: checkbox, radio, and group-box styles are filtered out; verify a scripted dialog mixing push buttons with those controls returns only the push buttons.
- [ ] 4.3 Exclude disabled and invisible controls; verify each is omitted.
- [ ] 4.4 Add label matching that strips `&`, trims, and matches exactly or case-insensitively; verify `"Save"` matches a `"&Save"` button and a non-matching label yields `error = "button_not_found"` with no control activated.

## 5. resolve-blocker button targeting

- [ ] 5.1 Extend the `resolve-blocker` parser (`unity_puer_exec_surface.py:66-69`) with `--action click` plus `--hwnd <int>` and `--button <label>`; verify `resolve-blocker --help` lists them and that `click` without `--hwnd` or `--button` is a usage error.
- [ ] 5.2 Restrict `--action cancel` to `safe_mode_dialog` and return `status = "resolution_failed"` with `error = "action_not_supported_for_blocker"` for any other blocker type; verify a save-scene dialog is rejected and no control is activated.
- [ ] 5.3 Re-validate the supplied `hwnd` before acting: it must still be a visible titled window owned by the requested project's Editor pid; verify a stale or foreign handle yields `error = "window_not_found"` with no control activated.
- [ ] 5.4 Route a click past the `multiple_supported_blockers` rule: an explicit `--hwnd` resolves even when several dialogs are present; verify with a tree containing two blocking dialogs.
- [ ] 5.5 Apply the existing disappearance confirmation to clicks, returning `error = "click_not_confirmed"` when the dialog persists; verify with a scripted dialog that never disappears.

## 6. Click chain

- [ ] 6.1 Implement message-level priority for non-Safe-Mode dialogs: button message, then command message, then posted key messages; verify the harness records no `SetForegroundWindow` call when the first level succeeds.
- [ ] 6.2 Keep Safe Mode on the existing `SetForegroundWindow` + `keybd_event` path (`_click_via_keyboard`); verify a Safe Mode resolution still records the foreground call and does not use the new chain.

## 7. Help surface and guidance

- [ ] 7.1 Update `resolve-blocker` help (`help_surface.py:276-306`) to document `--action click --hwnd --button`, its Safe-Mode-only `cancel` rule, and the new `window_not_found` / `button_not_found` errors; verify `resolve-blocker --help`, `--help-args`, and `--help-status` render the new content.
- [ ] 7.2 Repoint guidance templates that hardcode `--action cancel` (`help_surface.py:893-908`, `:1313-1321`) so `cancel` is suggested only for `safe_mode_dialog` and the button-targeted form otherwise, with no `argv` for the click form; verify no guidance entry suggests `cancel` for a non-Safe-Mode blocker type.
- [ ] 7.3 Update the `(resolve-blocker, resolution_failed)` `situation` text to cover both the stale-handle and unmatched-label cases; verify the CLI does not inspect `error` to select the candidate.
- [ ] 7.4 Run the command-table drift test (`tests/test_unity_session_cli.py:2486`) and verify all six command tables still agree.

## 8. Existing test migration

- [ ] 8.1 Update `tests/test_real_host_integration.py` save-scene resolution tests (`:836`, `:931`) to use `--action click --hwnd --button "Cancel"`; verify the `hwnd` is read from the observed blocker payload.
- [ ] 8.2 Add a real-host assertion that `--action cancel` on a save-scene dialog returns `action_not_supported_for_blocker` and leaves the dialog present; verify unsaved scene changes survive.
- [ ] 8.3 Add real-host coverage for an unknown dialog: trigger a Unity modal dialog with no catalog entry and assert `blocker.type = "unknown_modal_dialog"` plus `hwnd`, `title`, `body`, `buttons`; verify by running with `UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1`.
- [ ] 8.4 Add a real-host check that open non-blocking Editor windows (Preferences, Project Settings) are not reported as blockers; verify on a host machine with those windows open.

## 9. Host spikes and closeout

- [ ] 9.1 Run host spike H1 (owner-disabled detection against Unity's real dialogs, false-positive rate vs Preferences / Project Settings / Build Settings) and record the result in the change directory; verify the D2 downgrade fallback contains any observed false positive.
- [ ] 9.2 Run host spike H2 (does the Safe Mode dialog respond to command or posted key messages) and record the result; verify the Safe Mode exemption in D5 remains correct either way.
- [ ] 9.3 Run the full mock unit suite and verify it passes; confirm the fake-user32 harness covers the D2 downgrade branch, the D4 exclusion rules, and `button_not_found`.
- [ ] 9.4 Run `openspec validate --change generalize-modal-dialog --strict` and verify it reports no errors.
- [ ] 9.5 Confirm the durable spec deltas match the change's five capability files and touch no unrelated requirement; then recommend `git commit`, `openspec archive generalize-modal-dialog`, and a final `git commit`.
