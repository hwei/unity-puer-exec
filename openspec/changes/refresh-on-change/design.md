## Context

See `proposal.md` for motivation. This design answers the "how" for a server-side, on-demand refresh that fires only when there is something to compile.

Three facts about the current implementation shape every decision here.

**1. The server never waits for compilation.** `HandleExecAsync` enqueues `AssetDatabase.Refresh()` onto `MainThreadActions`, awaits only the enqueued action, and returns `{"refreshed":true}` immediately. Compile-settle is entirely CLI-side: `run_exec` calls `_ensure_project_session_ready_after_refresh` (project-path mode) or `_settle_base_url_after_refresh` (base-url mode), and only then submits the real script. That two-request shape is load-bearing, not incidental.

**2. Domain reload tears down the listener.** `AssemblyReloadEvents.beforeAssemblyReload += Stop` stops the listener before every reload, and `Start()` regenerates `sessionMarker`. A request that tried to await the compile settle server-side would be interrupted by the very reload it is waiting for. This is why fact 1 exists and why server-side settle is not an option.

**3. Watcher callbacks are off the main thread.** `OnEditorUpdate` is the sole main-thread pump; it drains `MainThreadActions` inside the Editor update loop. A `FileSystemWatcher` callback runs on a threadpool thread, so it must never touch Unity APIs. It may only write to a thread-safe collection.

An additional constraint arrived from the flag-removal decision: `cli_version.py` compares CLI and bridge versions for strict equality, and `help_surface.py` documents that the two halves ship as one release with no bypass. There is no supported CLI/bridge version skew, so nothing in this design needs a compatibility shim for one.

### What this change inherits from `stop-foreground-nudges`

That archived change removed `SetForegroundWindow` from `run_exec` and `run_wait_for_exec`. Its proposal stated the consequence explicitly: a plain `exec` after a C# edit no longer has an implicit trigger for Unity's ambient auto-refresh, and automating that case was deferred to `refresh-on-change`. So the finding that still holds is *the CLI does not implicitly refresh*, and the gap this design closes is *making the refresh automatic again without buying it with focus theft*.

### Why some of this belongs in `config.yaml` context and not in `specs/`

`openspec/config.yaml` context records what the repository *is* — the product halves, the external validation host, the fact that OpenSpec is canonical. It is guidance for whoever writes artifacts, not a behavior contract. The settled-import timestamp, the watcher's path filter, and the `refresh` diagnostics block are observable product behavior with testable consequences, so they belong in `openspec/specs/`, not in config context. This design names concrete types and hooks only to justify decisions; the specs assert behavior, never those names.

## Goals / Non-Goals

**Goals:**

- Make refresh automatic for compile-triggering changes, with no caller action and no unconditional per-exec cost.
- Keep the no-change path O(1) — no project-wide walk per exec.
- Make every refresh decision observable, because precision is the open question.
- Delete `--refresh-before-exec` rather than demote it, since every job it did is either automated or physically impossible.

**Non-Goals:**

- No refresh of non-code assets. Explicitly out of scope — see Decision 2.
- No server-side compile settle. Foreclosed by fact 2.
- No user-facing switch to force, disable, or tune the watcher. The CLI and bridge ship as one versioned release; a tuning knob would be surface area for a problem that should be fixed in the watcher.
- No change to the stale-module fingerprint contract. Fewer domain reloads mean fewer fingerprint resets, which is a performance consequence, not a contract change.
- No refresh-storm backstop beyond what the settled-import timestamp already provides. If measurement shows storms, the fix belongs in the filter, not in a rate limit.

## Decisions

### Decision 1: Delete `--refresh-before-exec` in this change

The flag carried three jobs. None survives.

```
1. Make a C# edit visible before the next exec
   -> watcher + install-time baseline walk take over   -> redundant

2. Force a refresh during play mode
   -> Unity defers all compilation until play exits    -> physically impossible
                                                          the flag was making a promise
                                                          it could not keep

3. Trigger recompilation after fixing compile errors
   -> "fixing" is itself a file write                  -> redundant
      the watcher sees it; the next exec refreshes
```

Job 3 deserves the detail: `help_surface.py` tells callers three separate times to "re-run with `--refresh-before-exec` to trigger recompilation" after fixing C# errors. But fixing a C# error means writing a `.cs` file, which the watcher observes, which triggers the automatic refresh. The guidance reduces to "re-run `exec`".

Deletion follows the repository's own precedent for a removed flag. `--include-log-offset` keeps its `add_argument` entry marked `# removed; emits usage error` and raises a machine-readable usage failure with a `situation` pointing at the replacement. `--refresh-before-exec` gets the same treatment: retained in the parser so a stale caller gets an actionable error instead of `unrecognized arguments`.

Removing the flag also resolves the play-mode question before it can arise. There is no forced path left to conflict with the play-mode skip, so the skip is unconditional.

Net effect on implementation size is a reduction, though smaller than it first appears. The two-request shape stays (fact 2). What disappears is the JS-side `AssetDatabase.Refresh()` template, the synthesized refresh request, the `PHASE_REFRESHING` pending-exec plumbing, the `refresh_before_exec` protocol field, and one dead condition: `if (!request.refresh_before_exec && TrySnapshotCompileErrors(...))` at `UnityPuerExecServer.cs:640` sits after an early `return` for the true case, so the guard is always true.

### Decision 2: Watch compile-triggering paths only, not import-triggering paths

The proposal specified "import-triggering extensions" and then named its own false-positive sources: Unity's import writes `.meta` files, and scene saves write `.unity`. Both are real changes that never trigger a compilation. Since compilation is the only reason a refresh matters to script execution, the filter is narrowed to what can cause one:

```
  .cs                 included   script source
  .asmdef / .asmref   included   assembly definition
  .rsp                included   response file, changes compiler invocation

  .unity              excluded   scene save, no compile
  .prefab             excluded   asset save, no compile
  .meta               excluded   Unity's own import bookkeeping
  textures / audio /  excluded   asset import, no compile
  other non-code
```

Two benefits. The false-positive class the proposal identified is gone by construction. And a subtle hole closes: importing a non-code asset produces no compilation, so no completion hook fires, so a single settled-import timestamp would never advance — every later exec would see the same file as new and refresh forever. Excluding those paths removes the hole rather than patching it.

The cost is accepted and must be stated in help: changing a texture or prefab no longer triggers an automatic refresh. Scripts that need an uncompiled asset re-imported are out of scope, and a caller that truly needs the import has `AssetDatabase.Refresh()` available through the bridge.

Because this is a deliberate, user-visible narrowing, help MUST name it — not merely imply it from the extension list. See `formal-cli-contract` and the `import-change-refresh` spec.

### Decision 3: One project-wide settled-import timestamp, advanced only by Unity's completion hooks

The proposal chose a single timestamp over a per-path map. That choice has a hard correctness consequence that must be designed around, not discovered later.

Importing a file does not change its mtime. So if nothing advances the timestamp, a file written at T1 stays newer than the timestamp forever, and every subsequent exec refreshes:

```
write A.cs     mtime = T1
exec           T1 > last_settle  -> refresh      correct
import done    mtime still T1                    <- the trap
exec           T1 > last_settle  -> refresh      infinite
```

Therefore the timestamp SHALL be advanced only by Unity's own completion signals, never by the exec path:

```
CompilationPipeline.compilationFinished        covers .cs / .asmdef / .rsp   primary
AssemblyReloadEvents.afterAssemblyReload       covers reload completion
```

`compilationStarted` and `assemblyCompilationFinished` are already subscribed in the static constructor, so adding a completion hook is cheap. `afterAssemblyReload` is new; `beforeAssemblyReload` is already wired for `Stop`, so the pair is natural.

**Verified during implementation.** Both completion hooks exist in the Unity version this package targets. The package declares `"unity": "2022.3"` and the validation host runs `2022.3.62f2`; inspecting `UnityEditor.CoreModule.dll` / `UnityEditor.CoreModule.xml` from the installed `2022.3.62f2` Editor confirms `CompilationPipeline.compilationFinished(System.Action<System.Object>)` and `AssemblyReloadEvents.afterAssemblyReload(UnityEditor.AssemblyReloadEvents.AssemblyReloadCallback)`. The event is therefore the primary advance source and the `afterAssemblyReload`-only fallback is not needed. Existing subscriptions at implementation time: `CompilationPipeline.compilationStarted` and `CompilationPipeline.assemblyCompilationFinished` (both in the static constructor), plus `AssemblyReloadEvents.beforeAssemblyReload` (wired to `Stop`). The completion subscriptions added by this change are `CompilationPipeline.compilationFinished` and `AssemblyReloadEvents.afterAssemblyReload`.

Known boundary, accepted: a file written while a compilation is in flight gets covered by the completion of that compilation and is missed once. The next edit self-heals. The alternative — refusing to advance while any candidate is pending — trades a rare miss for a liveliness risk, which is worse.

Persistence across domain reload is required for the same reason as the watcher's in-memory state: reload resets static fields. `SessionState` is already used for the activation flag and `Temp/UnityPuerExec/` is already used for endpoint publication, so either precedent fits. The spec asserts only that the timestamp survives reload, not which mechanism provides it.

### Decision 4: Watcher is an accelerator; three gaps force a fallback

Three failure modes can make the watcher silent about a real change:

```
InternalBufferOverflowException    large projects drop events
changes before the CLI attached    invisible to a watcher installed later
domain reload                      resets in-memory watcher state
```

Two responses, both of which mark dirty rather than silently missing the change:

- An `Error` event — including buffer overflow — marks dirty.
- An install-time baseline walk marks dirty. This is the only full project walk, and it happens once when the watcher is installed, not per exec. It is also what makes the "changes before attach" gap safe: the walk runs against the persisted timestamp, so anything already pending is caught.

So the no-change path is O(1) — no events, no stat, no refresh — while correctness never depends on the watcher having seen everything.

### Decision 5: The server reports the refresh decision; the CLI reacts

With the flag gone, the CLI cannot know whether a refresh happened. There is only one workable shape: the server includes a `refresh` block in the exec response, and the CLI settles only when the server reports it triggered one.

The alternative — CLI probes health for refresh state before deciding — costs a round trip and races the compile window in project-path mode. Rejected.

The block carries `triggered`, `reason`, `paths_changed`, `skipped_reason`, `settle_outcome`, and `elapsed_ms`. These are part of the change rather than a follow-up precisely because the false-positive rate is unmeasured; until it is measured on a real project, the diagnostics are the only way to tell precision from luck.

### Decision 6: Play mode skips the refresh but preserves the dirty signal

Unity defers compilation while in play mode, so refreshing there would wait for a compile that will not start. The skip MUST be visible via `skipped_reason` rather than silent.

The critical detail: skipping MUST NOT clear the dirty signal. If it did, the change would be lost permanently once play mode exited. The signal survives, and the first exec after play exits refreshes.

## Risks / Trade-offs

**[Watcher false positives from Unity's own writes]** → Narrowed the filter to compile-triggering extensions (Decision 2), which removes the class the proposal identified. Residual risk is measured, not guessed: `paths_changed` and `reason` are always populated when a refresh triggers.

**[Infinite refresh loop]** → The timestamp advances only on Unity completion hooks (Decision 3), never on the exec path. This is the single highest-severity failure mode in the design; it is a spec requirement, not an implementation note.

**[Missed change when the watcher is silent]** → Two independent dirty markers: error events and the install-time baseline walk (Decision 4).

**[Change written during an in-flight compilation is missed once]** → Accepted (Decision 3). Self-heals on the next edit. A liveliness bug would be worse than a one-shot miss.

**[Deleting a documented flag removes the manual escape hatch]** → The strict version-equality gate means no supported caller is stranded on an old CLI. Residual scripts passing the flag get an actionable usage error, not a parse failure. If the watcher misbehaves after shipping, the fix belongs in the watcher, and the diagnostics exist to make that diagnosable.

**[Non-code asset changes no longer auto-refresh]** → Accepted and documented in help (Decision 2). Out of scope by design.

**[No tuning knob]** → If the watcher causes trouble on a large project, the fix is in the filter or the debounce, not in a caller-facing switch that would Balkanize behavior across callers.

## Migration Plan

1. Editor side: settled-import timestamp with persisted storage, watcher with the compile-triggering filter and debounce, dirty-signal fallback, refresh decision wired into the exec path through the existing `MainThreadActions` queue. Confirm `CompilationPipeline.compilationFinished` exists first; fall back to `afterAssemblyReload` alone if it does not.
2. Protocol: add the `refresh` diagnostics block and remove the `refresh_before_exec` field in the same step. Keeping it accepted-but-ignored would be a dead field a caller could come to depend on; the version gate already makes a mixed installation unsupported.
3. CLI: delete the synthesized refresh request and `PHASE_REFRESHING` plumbing, keep the compile-settle machinery, react to the server-reported `refresh` block, convert `--refresh-before-exec` to a usage-error shim.
4. Help: rewrite the 14 `--refresh-before-exec` sites. Sites that said "re-run with `--refresh-before-exec` to trigger recompilation" become "re-run `exec`" — the file write is itself the trigger. Add the explicit statement that only code changes are watched.
5. Tests: mock coverage for the decision logic including the loop-breaking case; real-host coverage for watcher precision and false-positive rate.
6. Archive only after real-host evidence confirms the false-positive rate is acceptable.

Rollback: revert the pair together. The version gate means a mixed installation refuses to act rather than half-working, so there is no supported intermediate state.
