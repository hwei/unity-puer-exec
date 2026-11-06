# Tasks

## 1. Decide the design on the real host

- [ ] 1.1 Run probe cases A–D from design D3 with a `.tmp/` probe. Start from a git-clean host with `PlayerSettings.runInBackground` set to `0`. For B–D, make the package change as a local edit that is either kept for task 2.1 or reverted. Record each case's outcome in a `validation-transcript.md` in this change. Set `assumption_state` in `meta.yaml`: `valid` if A reproduces and B, C, D pass; `valid` with a note that the D2 fallback is required if only C fails; otherwise `invalid`, and stop to revisit the design. Verify by checking that the transcript names the branch taken and the host's `ProjectSettings.asset` is restored from git

## 2. Package fix

- [ ] 2.1 Remove the edit-mode `Application.runInBackground = true` assignment from `UnityPuerExecServer.HandlePlayModeAsync`. Rewrite the inline comments there and the doc comment in `UnityPuerExecPlayMode.cs` to state the actual guarantee: the override is applied only once play mode is entered. Verify by having `tests/test_package_layout.py` assert that the handler no longer contains the assignment while the hook still does, and confirm the full mocked suite in how-to-run.md is green
- [ ] 2.2 Only if 1.1 took the D2 branch: add the `SessionState` snapshot and restore it through `PlayerSettings.runInBackground` on `EnteredEditMode` and `EditorApplication.quitting`, with matching `test_package_layout.py` assertions. Otherwise mark this task done with a note that 1.1 showed it is not needed. Verify by checking either the passing assertions or the note

## 3. CLI help wording

- [ ] 3.1 Update `play` help in `cli/python/help_surface.py` so the run-in-background text matches the guarantee from 2.1/2.2 (applied only after entering play mode, and not persisted to Player Settings). Verify with `tests/test_unity_session_cli.py::test_play_help_discloses_run_in_background_override_and_option`, adjusting the assertions to the new wording, and confirm it passes

## 4. Real-host regression

- [ ] 4.1 Add two pristine-process real-host cases next to `PlayModeCompileBlockRealHostTests`, as design D4 describes: stop-then-close and close-while-playing. Each sets the host value to `0`, compares the `ProjectSettings.asset` bytes before and after, and restores the host value. Verify that the cases fail against the pre-change package (case A of the probe is the reference) and pass after the fix
- [ ] 4.2 Run `PlayModeCompileBlockRealHostTests` plus the new cases on the real host, then confirm `git -C <host> status` shows no `ProjectSettings.asset` diff. Add the run summary to `validation-transcript.md`, and confirm `meta.yaml` evidence includes `host-validation`

## Workflow follow-up

- Apply closeout per AGENTS.md, then `git commit`, `openspec archive stop-play-persisting-run-in-background`, and the final `git commit` when the human asks.
