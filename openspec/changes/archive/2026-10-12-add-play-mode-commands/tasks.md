## 1. Rename `ensure-stopped` to `ensure-closed`

- [x] 1.1 Add an alias table to `command_registry.py` and rename the command to `ensure-closed`. Derive the alias's parser entry, help tiers, and guidance from the table, and add the `deprecated` field to alias responses. Verify: the "invocable set == documented set" test passes, and a new test shows `ensure-stopped` and `ensure-closed` give identical results apart from the `deprecated` field.
- [x] 1.2 Update the runtime, `unity_session*.py`, help text, and tests to the new name. Top-level help must describe `ensure-closed` as closing the Editor process. Verify: `python -m unittest tests.test_unity_session_cli tests.test_unity_session_modules` passes, and a grep finds `ensure-stopped` only in the alias table, alias tests, and deprecation text.

## 2. Server: play state and play control

- [x] 2.1 Derive `play_state` in `OnEditorUpdate` (design D1 table) and publish it in the health response. Verify: C# compiles, and real-host `/health` reports `edit`, `playing`, and `paused` as the Editor is toggled.
- [x] 2.2 Add `POST /play-mode` (play / pause / stop / resume-on-play) and run it on the main thread. Return the observed play state, and reject `pause` in edit mode with `invalid_play_state`. Verify: real-host probes move the Editor through each state.
- [x] 2.3 Store the run-in-background request in `SessionState` and apply it on `EnteredPlayMode` from an `[InitializeOnLoad]` hook. Never write `PlayerSettings`. Verify: with Reload Domain both on and off, `Application.runInBackground` is true after a forced play, and `git status` on the host shows `ProjectSettings.asset` unchanged.

## 3. CLI commands

- [x] 3.1 Extract the refresh-decision and settle path that `exec` uses so `play` can call it without an exec request. Verify: the existing `AutomaticRefresh*` unit tests pass unchanged.
- [x] 3.2 Implement `play`: prepare the Editor in project mode, settle pending code first (return `unity_compile_error` without entering play mode), post `/play-mode`, wait for `playing` across a domain reload, and disclose `run_in_background`. Add `--no-run-in-background` and `--timeout-seconds`. Verify: unit tests cover a clean pre-settle, a compile-error abort, `already_in_state`, `resumed`, a reload during entering, and a timeout returning `running`.
- [x] 3.3 Implement `pause` and `stop` (design D4). Before posting, `stop` reads `compile_generation` and `refresh.pending` from health. It then waits for `edit` on the compile-scale budget when a compile may follow (design D2), and calls `wait_for_compile_cycle(compile_generation_baseline=…)`. After a settle, it reads compile errors through the existing compile-error path to fill `compile_errors_total`. It reports `compile: {outcome, edge, compile_errors_total}` in the `wait-for-compile` vocabulary. Verify: unit tests cover pause in edit mode → `invalid_play_state`; stop from `paused`; stop with and without a pending change; a generation advance with the endpoint down for the whole exit → `compile_settled` with `edge: "generation_advance"`; `not_pending` plus a generation advance → `compile_settled`; a long unreachable window during exit that does not return `running` or a failure; and stop with compile errors → completed, `compile_errors_total > 0`, plus a `get-compile-errors` next step.
- [x] 3.4 Surface modal blockers during transitions in the same shape `exec` uses, and map an absent `/play-mode` to the version-mismatch result. Verify: unit tests cover a blocker during `stop` and an old package.
- [x] 3.5 Register `play` / `pause` / `stop` in "Primary Execution" and add help tiers, `--help-status`, and guidance entries. Update the PlayMode help to present the commands as the normal path. Switch `_PLAY_MODE_EXIT_STEPS` (`help_surface.py`) to `stop`. It is used by the merged `exec` / `wait-for-exec` warning guidance and by the `wait-for-compile` `compile_blocked` guidance, so update the `disclose-play-mode-block-in-wait-for-exec` merged-guidance tests (exit step plus `wait-for-result-marker`) to match. Verify: help-content tests assert the PlayMode wording, the run-in-background disclosure and option, and that no guidance still uses the exec-based stop.

## 4. Specs

- [x] 4.1 Validate the deltas. Verify: `openspec validate add-play-mode-commands --strict` passes.

## 5. Real-host confirmation

- [x] 5.1 Add real-host cases: `play` from edit mode with a pending `.cs` change (expect a pre-settle, then `playing`), `pause`, `play` (expect `resumed`), and `stop` (expect `edit` plus `compile.outcome: "compile_settled"` with `edge: "generation_advance"`). Also add the `play` compile-error abort. Verify: the cases pass under the opt-in gate and skip cleanly without a host.
- [x] 5.2 On the host, with the Editor unfocused, confirm that a forced play session keeps advancing frames and that `--no-run-in-background` does not when the project setting is off. Record whether Interaction Mode throttling still matters. Verify: the transcript is recorded in `meta.yaml` evidence and any throttling gap is listed as a follow-up candidate.

## Workflow follow-up

- Prerequisites `surface-play-mode-compile-block`, `observe-compile-across-domain-reload`, `add-compile-generation-signal`, and `disclose-play-mode-block-in-wait-for-exec` are archived. `stop` consumes the `compile_generation` signal that `add-compile-generation-signal` shipped (design D4).
- After review, commit, run `openspec archive add-play-mode-commands`, and commit again.
