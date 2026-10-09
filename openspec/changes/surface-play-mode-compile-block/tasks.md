## 1. Reproduce "cannot stop play mode"

- [ ] 1.1 On the validation host, enter play mode with a pending compile-triggering `.cs` change, then stop play mode through `exec` (`EditorApplication.isPlaying = false`) and record what happens: the exec result, the play state over time, `/health`, and the project-private `Editor.log`. Run it once with each "Script Changes While Playing" setting and once with Enter Play Mode Options (Reload Domain disabled) on. Verify: the record names which design D6 hypothesis held, or states that none reproduced.
- [ ] 1.2 Act on the finding. For hypotheses 1 or 2, add the CLI or guidance fix to group 4. For 3, confirm that `get-blocker-state` reports the dialog, or open a follow-up. For 4 or 5, write the host-specific note or the hand-off into `add-play-mode-commands/design.md`. Verify: the change records an explicit outcome for the stop failure.

## 2. Health reports the play-time compile preference

- [ ] 2.1 Sample `EditorPrefs.GetInt("ScriptCompilationDuringPlay")` in `OnEditorUpdate` and add `script_changes_while_playing` to the health suppression block, with an `unknown` fallback. Verify: a C# compile check passes and real-host `/health` in play mode shows the value matching the Preferences UI.
- [ ] 2.2 Cover the mapping and the `unknown` fallback in the Python-side health parsing tests. Verify: `python -m unittest tests.test_unity_session_cli` passes.

## 3. Exec warning for a play-mode compile block

- [ ] 3.1 In the exec result path, when `refresh.skipped_reason == "play_mode"` and the decision saw pending paths, attach `compile_blocked` and turn a `completed` result into `status: "warning"`, `warning: "compile_blocked_by_play_mode"`, with `warning_detail`. Keep a failure status or an existing async warning unchanged, and attach the object in every case. Verify: unit tests cover completed→warning, nothing pending→completed, a throwing script→failure with the object, and an async warning keeping its code.
- [ ] 3.2 Add `situation` and `next_steps` for the warning in `help_surface.py`: an exec that exits play mode, confirmation of the play state, then `wait-for-compile`. Add the status to `exec --help-status`. Verify: help-content tests assert the situation text and that no step mentions `RequestScriptCompilation`.

## 4. wait-for-compile `compile_blocked` outcome

- [ ] 4.1 Before the appear phase, return `result.status: "compile_blocked"` (`compile_observed: false`, `reason: "play_mode"`) when health shows not compiling, a pending change, and suppression for `play_mode`. An observed compile edge still settles normally. Verify: clock-modelled unit tests show an immediate return with no appear-window wait, `no_compile_observed` still returned when nothing is pending, and an in-progress compile still settling.
- [ ] 4.2 Add guidance and `--help-status` text for `compile_blocked`, and make the existing `no_compile_observed` text stop presenting `RequestScriptCompilation()` as the fix when the Editor is playing. Verify: help-content tests pass.
- [ ] 4.3 Land any CLI or guidance fix found in 1.2. Verify: a unit or real-host test reproduces the original failure and passes after the fix.

## 5. Specs and real-host confirmation

- [ ] 5.1 Validate the deltas. Verify: `openspec validate surface-play-mode-compile-block --strict` passes.
- [ ] 5.2 Add a real-host case: enter play mode, touch a `.cs` file, run `exec` and expect the warning plus `compile_blocked`, run `wait-for-compile` and expect `compile_blocked`, exit play mode, then `wait-for-compile` expecting a completed compile. Verify: the case passes under the opt-in real-host gate and skips cleanly without a host.
- [ ] 5.3 Update `meta.yaml` (`updated_at`, `evidence`) and record the real-host transcript. Verify: `python tools/openspec_backlog.py list` shows the change with its tasks complete.

## Workflow follow-up

- After review, commit, run `openspec archive surface-play-mode-compile-block`, and commit again.
- Archiving unblocks `add-play-mode-commands`.
