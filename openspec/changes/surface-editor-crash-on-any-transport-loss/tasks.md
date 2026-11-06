# Tasks

## 1. Shared Editor-exit check and exec widening

- [x] 1.1 Add the shared pid-based "published Editor exited" helper (design D1), and re-express `_wait_for_journaled_editor_exit` on top of it. Verify that the existing exec crash tests in `tests/test_unity_session_cli.py` still pass unchanged
- [x] 1.2 Widen the in-flight exec crash branch so that `empty_response` also runs the journal grace check (design D2, exec bullet). Verify with new mocked tests: an empty body plus a dead journalled pid gives `editor_crashed_during_request` / exit 26; an empty body plus a live pid keeps `empty_response`

## 2. Play-mode and compile-query commands

- [x] 2.1 In `_post_play_mode` and the play-mode probe loop, check the pid on every transport-drop iteration, and run one grace watch at the budget edge (design D2). Return the command-level crash payload (design D3, spec "The command-level crash response carries evidence"). Verify with mocked tests for `play`, `pause` and `stop`: a dead pid returns exit 26 without consuming the budget and without calling `ensure_session_ready` again; a live pid keeps the existing re-resolve and retry tests green
- [x] 2.2 Apply the same check to `wait-for-compile`, `get-compile-errors` and `get-compile-warnings` in project mode. Verify with one mocked crash test per command, plus the existing tests for those commands
- [ ] 2.3 Add `editor_crashed_during_request` (exit 26) to the `--help-status` tables of all six commands, and the base-url clause from design D4. Verify with help tests asserting that the status appears for each command

## 3. Real-host evidence

- [ ] 3.1 Add two pristine-process real-host cases (design D5): a `play` that crashes on entering play mode through a temp-asset `ForceCrash` script, and an `exec` that calls `ForceCrash`. Both assert exit 26, `editor_pid`, `crash_report_dir`, and a `play` duration well under `--timeout-seconds`. Clean up the temp script. Verify that the cases fail on the pre-change CLI (where `play` exhausts its budget and reports a transport status) and pass after
- [ ] 3.2 Run the new cases plus `PlayModeCompileBlockRealHostTests` on the real host. Record the summary in a `validation-transcript.md` in this change, and confirm the host is clean afterwards (`cleanup_validation_host.py`, `--restore-manifest`, `--restore-embedded-shadow`, empty host `git status`)

## 4. Integration check

- [ ] 4.1 Run the full mocked suite listed in how-to-run.md and confirm it is green. Run `openspec validate surface-editor-crash-on-any-transport-loss --strict` and confirm it passes

## Workflow follow-up

- Apply closeout per AGENTS.md, then `git commit`, `openspec archive surface-editor-crash-on-any-transport-loss`, and the final `git commit` when the human asks.
