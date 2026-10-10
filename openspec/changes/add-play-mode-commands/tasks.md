## 1. Rename `ensure-stopped` to `ensure-closed`

- [ ] 1.1 Add an alias table to `command_registry.py` and rename the command to `ensure-closed`. Derive the alias's parser entry, help tiers, and guidance from the table, and add the `deprecated` field to alias responses. Verify: the "invocable set == documented set" test passes, and a new test shows `ensure-stopped` and `ensure-closed` give identical results apart from the `deprecated` field.
- [ ] 1.2 Update the runtime, `unity_session*.py`, help text, and tests to the new name. Top-level help must describe `ensure-closed` as closing the Editor process. Verify: `python -m unittest tests.test_unity_session_cli tests.test_unity_session_modules` passes, and a grep finds `ensure-stopped` only in the alias table, alias tests, and deprecation text.

## 2. Server: play state and play control

- [ ] 2.1 Derive `play_state` in `OnEditorUpdate` (design D1 table) and publish it in the health response. Verify: C# compiles, and real-host `/health` reports `edit`, `playing`, and `paused` as the Editor is toggled.
- [ ] 2.2 Add `POST /play-mode` (play / pause / stop / resume-on-play) and run it on the main thread. Return the observed play state, and reject `pause` in edit mode with `invalid_play_state`. Verify: real-host probes move the Editor through each state.
- [ ] 2.3 Store the run-in-background request in `SessionState` and apply it on `EnteredPlayMode` from an `[InitializeOnLoad]` hook. Never write `PlayerSettings`. Verify: with Reload Domain both on and off, `Application.runInBackground` is true after a forced play, and `git status` on the host shows `ProjectSettings.asset` unchanged.

## 3. CLI commands

- [ ] 3.1 Extract the refresh-decision and settle path that `exec` uses so `play` can call it without an exec request. Verify: the existing `AutomaticRefresh*` unit tests pass unchanged.
- [ ] 3.2 Implement `play`: prepare the Editor in project mode, settle pending code first (return `unity_compile_error` without entering play mode), post `/play-mode`, wait for `playing` across a domain reload, and disclose `run_in_background`. Add `--no-run-in-background` and `--timeout-seconds`. Verify: unit tests cover a clean pre-settle, a compile-error abort, `already_in_state`, `resumed`, a reload during entering, and a timeout returning `running`.
- [ ] 3.3 Implement `pause` and `stop`. `stop` reads pending state, waits for `edit`, and then settles the deferred compile on the compile-scale budget, reporting the `compile` outcome. Fold in any handling required by the `surface-play-mode-compile-block` D6 outcome. Detect the deferred compile's completion with the signal chosen by `observe-compile-across-domain-reload`, so a compile hidden behind the play-exit domain reload is not reported as `no_compile_observed`. Verify: unit tests cover pause in edit mode → `invalid_play_state`, stop with and without a pending change, and stop with compile errors → completed plus a `get-compile-errors` next step.
- [ ] 3.4 Surface modal blockers during transitions in the same shape `exec` uses, and map an absent `/play-mode` to the version-mismatch result. Verify: unit tests cover a blocker during `stop` and an old package.
- [ ] 3.5 Register `play` / `pause` / `stop` in "Primary Execution" and add help tiers, `--help-status`, and guidance entries. Update the PlayMode help to present the commands as the normal path. Switch the `surface-play-mode-compile-block` `next_steps` to `stop`. Verify: help-content tests assert the PlayMode wording, the run-in-background disclosure and option, and that no guidance still uses the exec-based stop.

## 4. Specs

- [ ] 4.1 Validate the deltas. Verify: `openspec validate add-play-mode-commands --strict` passes.

## 5. Real-host confirmation

- [ ] 5.1 Add real-host cases: `play` from edit mode with a pending `.cs` change (expect a pre-settle, then `playing`), `pause`, `play` (expect `resumed`), and `stop` (expect `edit` plus a settled compile). Also add the `play` compile-error abort. Verify: the cases pass under the opt-in gate and skip cleanly without a host.
- [ ] 5.2 On the host, with the Editor unfocused, confirm that a forced play session keeps advancing frames and that `--no-run-in-background` does not when the project setting is off. Record whether Interaction Mode throttling still matters. Verify: the transcript is recorded in `meta.yaml` evidence and any throttling gap is listed as a follow-up candidate.

## Workflow follow-up

- `surface-play-mode-compile-block` is archived. Apply only after `observe-compile-across-domain-reload` has settled its compile-completion signal (`blocked_by`), because `stop` depends on it (design D4).
- After review, commit, run `openspec archive add-play-mode-commands`, and commit again.
