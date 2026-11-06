# Validation transcript — make-ensure-closed-close-gracefully

## Task 1.1 probe (2026-11-06): quit mechanism

- Probe: `.tmp/quit_mechanism_probe.py`, host `c3-client-tree2/Project`, Unity
  2022.3.62f2, `-force-gles30`. The host was prepared with
  `prepare_validation_host.py --clear-embedded-shadow` then
  `prepare_validation_host.py`, so the loaded package was the repository copy.
- Every case launched its own Editor through the CLI, then read `unity_pid` from
  `Temp/UnityPuerExec/endpoint.json`. `ProjectSettings.asset` was restored from
  the captured baseline bytes after each case.
- How "the setting was saved" is read: the probe writes
  `PlayerSettings.runInBackground = true` in memory only (no `SaveAssets`) and
  then checks whether the asset on disk moved `runInBackground: 0 -> 1`.
- How "the prompt appeared" is read: the probe polls
  `unity_modal_blockers.detect_modal_blocker(pid)` while the quit is pending.
- Two mechanisms, per design D1:

  - **A. CLI-side `CloseMainWindow`** — `(Get-Process -Id <pid>).CloseMainWindow()`
    against the published pid.
  - **B. Server-side quit action** — a temporary `/quit` endpoint action in
    `UnityPuerExecServer.cs` that replies first, then exits from the main thread.
    Reverted; the tree is clean.

### Mechanism A

| criterion | result |
|---|---|
| (a) clean exit, no crash report | PASS — `CloseMainWindow` returned `True`, Editor gone, `new_crashes: []` |
| (b) dirty in-memory setting saved | PASS — asset went `runInBackground: 0 -> 1` |
| (c) unsaved scene shows the save prompt | PASS — `save_modified_scenes_prompt` with buttons `&Save` / `&Don't Save` / `&Cancel`, resolved with an explicit `click` on `&Don't Save` |

`scene-close` evidence: `dirty_before: false, dirty: true` after
`EditorSceneManager.MarkSceneDirty`, then the blocker above appeared while the
quit was pending and the Editor exited cleanly after the explicit discard.

### Mechanism B

Attempt 1 — `EditorApplication.delayCall += … Exit(0)` registered directly from
the HTTP listener thread: the reply arrived, **no `delayCall` ever ran**, the
Editor stayed alive, no setting was saved. This is not the designed shape, just
the first cut.

Attempt 2 — the same `delayCall` registration enqueued on `MainThreadActions`:
still never fired; Editor stayed alive.

Attempt 3 (B′) — `EditorApplication.Exit(0)` called **directly** from the
main-thread action, i.e. with no script frame on the stack. This is the closest
faithful reading of "exit without a script frame":

| criterion | result |
|---|---|
| (a) clean exit, no crash report | PASS — `new_crashes: []` |
| (b) dirty in-memory setting saved | PASS — asset went `runInBackground: 0 -> 1` |
| (c) unsaved scene shows the save prompt | **FAIL — no blocker was ever detected; the Editor exited and the dirty scene was discarded** |

B(attempt 3) is therefore strictly worse than A: it saves project settings but
silently throws away unsaved scene work, which is the exact outcome design D2
exists to prevent. B as literally designed (`Exit` from `delayCall`) could not
even be made to run on this host.

### Decision

**Mechanism A — CLI-side `CloseMainWindow` — is chosen.** It is the only
mechanism that satisfies all three criteria, and it needs no package change, so
it also works against older package versions on disk. `assumption_state: valid`,
design D1's chosen mechanism is A.

Open point for task 2.1, to be handled there rather than hidden here:
`CloseMainWindow` returns `False` when the published process has no main window
(startup, minimized splash, batch mode). Design D1's risk entry already says to
treat that as "could not request quit" and escalate at the timeout with
`closed_via: killed` plus a diagnostic.

No new Unity crash report was created by any of the above: the crash directory
listing after each case added nothing.

## Host teardown

`prepare_validation_host.py --restore-manifest`, `--restore-embedded-shadow`,
`cleanup_validation_host.py`; host `git status --short` empty afterwards.
