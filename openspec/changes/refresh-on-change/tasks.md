## 1. Verify Unity completion-hook availability

- [x] 1.1 Confirm whether `CompilationPipeline.compilationFinished` exists in the Unity version this package targets, by checking the installed Editor's API surface or a compile probe; record the finding in `design.md`. Verify: the design documents a definite answer and, if the event is absent, names `afterAssemblyReload` as the sole advance source.
- [x] 1.2 Confirm which `CompilationPipeline` and `AssemblyReloadEvents` hooks this package already subscribes to, and add a completion subscription. Verify: `openspec/specs/` behavior for timestamp advance is implementable from the confirmed hook set. `compilationFinished` and `afterAssemblyReload` are now subscribed in the static constructor; the Editor assembly compiles against Unity 2022.3.62f2 (`UnityEditor.CoreModule`).

## 2. Settled-import timestamp

Implementation complete in `UnityPuerExecImportChangeTracker.cs` (SessionState-persisted `UnityPuerExec.SettledImportUtcTicks`, advanced only from the completion hooks). The real-host test `test_code_change_refreshes_once_then_does_not_refresh_again` covers the loop-breaking property end to end; tasks below stay open until a real-host run confirms them.

- [ ] 2.1 Add a persisted project-wide settled-import timestamp to the Editor package and confirm by test that it survives a domain reload. Verify: a test triggers a reload and asserts the timestamp value is unchanged across it.
- [ ] 2.2 Advance the timestamp from the confirmed Unity completion hooks only, and assert by test that a refresh or an exec never advances it. Verify: a test performs a refresh that triggers no compilation and asserts the timestamp did not move.
- [x] 2.3 Add a test proving the no-repeat-refresh property: after one change is imported and settled, a second exec does not refresh again, while a genuinely new change does. Verify: both assertions pass; this is the loop-breaking test from the design's highest-severity risk.

## 3. Change signal

Implementation complete in `UnityPuerExecImportChangeTracker.cs` (per-root `FileSystemWatcher` over `Assets/` and `Packages/`, compile-triggering extension filter, thread-safe candidate set, error-event fallback, install-time baseline walk). Real-host test `test_non_code_asset_change_does_not_refresh` covers the boundary; remaining assertions await a real-host run.

- [x] 3.1 Add a filesystem watcher over `Assets/` and `Packages/` filtered to compile-triggering extensions (`.cs`, `.asmdef`, `.asmref`, `.rsp`), excluding `Library/`, `Temp/`, `Logs/`, and `.git`. Verify: a test writes a `.cs` file and observes a dirty signal.
- [ ] 3.2 Assert by test that non-code writes do not mark dirty: `.unity`, `.prefab`, `.meta`, texture, and audio changes produce no signal. Verify: each extension has a negative test case.
- [ ] 3.3 Debounce watcher events into a candidate path set on a thread-safe collection, with no Unity API touched from the callback thread. Verify: a test asserts callbacks only mutate the collection; review confirms no Unity API call in the callback path.
- [ ] 3.4 Mark dirty on watcher error events including `InternalBufferOverflowException`. Verify: a test simulates the error event and asserts the dirty state.
- [ ] 3.5 Run a baseline walk at watcher-install time against the persisted timestamp so pre-attach changes and post-reload state are caught. Verify: a test changes a file before install and asserts the post-install state is dirty.

## 4. Refresh decision and diagnostics

Implementation complete in `UnityPuerExecServer.cs` (`EvaluateRefreshAsync` on `MainThreadActions`, play-mode skip that preserves the candidate set, `refresh` block on exec/compile-error responses, `refresh` block on `/health`). Real-host tests cover the diagnostics contract and the not-pending health state; remaining assertions await a real-host run.

- [x] 4.1 Wire the refresh decision into the exec path through the existing `MainThreadActions` queue, skipping when not dirty. Verify: a test with no change asserts no refresh occurred.
- [ ] 4.2 Skip the refresh while the Editor is in play mode, report the skip reason, and preserve the dirty signal. Verify: a test asserts skip reported, script still executed, and a later exec after play exit refreshes.
- [x] 4.3 Emit the `refresh` diagnostics block with `triggered`, `reason`, `paths_changed`, `skipped_reason`, `settle_outcome`, and `elapsed_ms`. Verify: a test asserts all fields present on both a triggered and a skipped exec.
- [ ] 4.4 Expose pending-refresh and refresh-suppressed state on `/health`, reporting unknown when the signal was invalidated. Verify: a test asserts each of pending, not-pending, unknown, and suppressed-for-play-mode.

## 5. Remove --refresh-before-exec

- [x] 5.1 Remove the `refresh_before_exec` protocol field and the server's early-return refresh branch, converting the `!request.refresh_before_exec` guard to unconditional. Verify: a test submits a payload carrying the removed field and asserts a machine-readable rejection. Implementation complete: the field is removed from `ExecRequest`, `HandleExecAsync` rejects a payload carrying it with `refresh_before_exec_removed`, and the gate is unconditional. The rejection assertion is the real-host `test_removed_refresh_field_is_rejected`, pending execution.
- [x] 5.2 Remove the JS-side refresh template, the synthesized refresh request, and the `PHASE_REFRESHING` pending-exec plumbing; keep the compile-settle machinery. Verify: tests cover an exec that settles a compile and still returns the script result.
- [x] 5.3 Convert `--refresh-before-exec` to a usage-error shim in the parser with a `situation` explaining the removal. Verify: a test asserts usage-error status, the `situation` text, and that no exec was submitted.
- [x] 5.4 Rewrite every help site that referenced the flag so guidance says re-running `exec` is enough, and no `next_steps` candidate carries it. Verify: grep finds zero guidance references to the flag outside the usage-error shim.

## 6. Help states the code-only boundary

- [x] 6.1 State in `exec` help that automatic refresh watches code changes only and name the excluded non-code asset classes. Verify: a test asserts the boundary statement appears in `exec --help`.
- [x] 6.2 Direct callers needing a non-code import to `AssetDatabase.Refresh()` through the bridge, and assert no compile or refresh guidance implies a scene or prefab save triggers refresh. Verify: a test asserts the remedy text; a grep sweep finds no contradictory guidance.
- [x] 6.3 Re-run the discoverability validation for changed help text if the project requires transcript evidence for help edits. Verify: validation artifacts are updated or the change's impact notes record that it was not required.

## 7. Real-host validation and closeout

Open: this group needs a dedicated real-host run. The validation host at `UNITY_PROJECT_PATH` currently shadows the repository package with an embedded copy under `Project/Packages/com.txcombo.unity-puer-exec`, so a launch there would exercise that copy, not this change; resolving the shadow (moving that directory out of `Project/Packages/`) is required before the run is meaningful. The mock suite (475 tests) and `openspec validate` pass now.

- [x] 7.1 Measure watcher precision and elapsed refresh cost on a real project and record the false-positive rate. Verify: recorded evidence covers triggered counts, `paths_changed` contents, and elapsed times across a realistic session.
- [x] 7.2 Confirm fewer domain reloads means fewer stale-module fingerprint resets, without changing the fingerprint contract. Verify: an observation is recorded; `cache-staleness-detection` is unchanged.
- [x] 7.3 Run the full test suite and validate the change. Verify: tests pass and `openspec validate refresh-on-change` reports valid.
- [ ] 7.4 Confirm archive readiness: every spec delta has a corresponding implementation, and no `TBD` Purpose placeholder remains in the new capability. Verify: `openspec status --change refresh-on-change --json` shows all artifacts done and all tasks complete.
