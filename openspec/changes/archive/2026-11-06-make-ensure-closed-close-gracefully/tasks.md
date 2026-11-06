# Tasks

## 1. Decide the quit mechanism on the real host

- [x] 1.1 With a `.tmp/` probe on the prepared host, compare design D1 mechanism A (`CloseMainWindow` on the published pid) with mechanism B (a temporary local package edit adding a delayCall `EditorApplication.Exit(0)` endpoint action, reverted afterwards). Check three things for each: (a) a clean exit with no crash report; (b) a dirty in-memory project setting is saved; (c) an unsaved scene shows the save prompt. Record the results in a `validation-transcript.md` in this change, and set `assumption_state` to `valid` with the chosen mechanism named in design D1. Verify by checking the transcript and confirming no new crash report in `%TEMP%/Unity/Editor/Crashes`

## 2. Graceful ensure-closed

- [x] 2.1 Implement the chosen quit request in `unity_session_process.ensure_closed`'s default mode: request quit, poll lockfile and blocker state, and escalate to a kill at the timeout. Add `result.closed_via` in `run_ensure_closed`. Verify with mocked tests for already_stopped, graceful, killed after timeout, quit request failed then killed, and `--immediate-kill` unchanged
- [x] 2.2 Report a supported modal blocker during the wait as `modal_blocked` (exit 19) without killing, with next steps `resolve-blocker` and `ensure-closed --immediate-kill`. Verify with a mocked test where the blocker appears mid-wait and the kill function is never called

## 3. exec guard and help

- [x] 3.1 Add the lexical `EditorApplication.Exit` pre-submit refusal to `exec` (design D4): status `editor_exit_in_script`, exit code 27, registered in the exec status tables. Verify with mocked tests for `--code` and `--file`, spacing variants, an unrelated script still submitted, and no session or launch call on refusal
- [x] 3.2 Rewrite the `ensure-closed` help (quick start, statuses, `closed_via`), the top-level command-list line, and the exec help: make ensure-closed the recommended close, add the `EditorApplication.Exit` crash warning, and remove the `exit.js` recommendation. Verify with help tests asserting the new wording and that `exit.js` no longer appears

## 4. Real-host evidence

- [x] 4.1 Switch `PlayModeRunInBackgroundPersistenceRealHostTests`' close helper to `ensure-closed` and assert `closed_via: graceful`. Add a real-host case that dirties the active scene and asserts that `ensure-closed` returns `modal_blocked` with the Editor still alive, then resolves the dialog and closes. Verify by running these cases plus `PlayModeCompileBlockRealHostTests` on the real host, recording the summary in `validation-transcript.md`, and confirming no new crash report and a clean host `git status` after teardown

## 5. Integration check

- [x] 5.1 Run the full mocked suite listed in how-to-run.md and confirm it is green. Run `openspec validate make-ensure-closed-close-gracefully --strict` and confirm it passes

## Workflow follow-up

- Apply closeout per AGENTS.md, then `git commit`, `openspec archive make-ensure-closed-close-gracefully`, and the final `git commit` when the human asks.
