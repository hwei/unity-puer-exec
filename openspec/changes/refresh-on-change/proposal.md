## Why

`--refresh-before-exec` is opt-in, so callers must remember that a C# edit needs a refresh before the next exec. The alternative to remembering is to refresh unconditionally, which was evaluated and rejected: in `--base-url` mode a refresh with no pending change burns the full appear window (`DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS = 10.0`, `unity_session_common.py:13`) before reporting `no_compile_observed`, and any refresh that does trigger a compile forces a domain reload that tears down the JsEnv and clears the local-module fingerprints tracked by `cache-staleness-detection`. Unconditional refresh trades a correctness footgun for a latency and state-reset regression.

The wanted shape is refresh that is automatic but only when there is something to import. A full mtime walk per exec is the obvious implementation and is probably cheap enough, but a `FileSystemWatcher` over import-triggering paths would make the no-change case O(1) and remove the walk entirely.

## What Changes

Direction decided, mechanism not yet validated:

- **Server-side, on-demand refresh.** The Editor side tracks a persisted `last_import_settle_utc` that survives domain reload, plus a dirty signal from a `FileSystemWatcher` over `Assets/` and `Packages/` filtered to import-triggering extensions and excluding `Library/`, `Temp/`, `Logs/`, and `.git`. Events debounce into a candidate path set; only those paths are stat'd against `last_import_settle_utc` to decide whether a refresh is actually needed. No events means no stat and no refresh.
- **Watcher is an accelerator, not the source of truth.** Three gaps force a fallback: `InternalBufferOverflowException` on large projects drops events; changes made before the CLI attached are invisible to a watcher installed later; and domain reload resets in-memory watcher state. An Error event or install-time baseline walk marks dirty rather than silently missing the change.
- **Play mode skips the automatic refresh.** Unity defers compilation while in play mode until play exits, so an automatic refresh there can stall waiting for a compile that will not start — the same class of hang as waiting on compile-settle during play. The skip needs to be visible (`refresh_skipped_reason`) rather than silent.
- **`--refresh-before-exec` becomes a forced override** rather than the only way to get a refresh. It stays for cases where the caller knows a refresh is needed and the watcher has no signal.
- **Observable, because precision is the open question.** Diagnostics carry `triggered`, `reason`, `paths_changed`, `skipped_reason`, `settle_outcome`, and `elapsed_ms`. The real risk is false positives: Unity's own import writes `.meta` files and scene saves write `.unity`, both of which are real changes that may not require a recompile. That rate is unknowable without measurement, so exposing these fields is part of the change rather than a follow-up.

## Open Before Implementation

- False-positive rate of the watcher signal against Unity's own writes, and whether debounce plus mtime comparison against `last_import_settle_utc` is sufficient filtering.
- Whether `SessionState` or a `Temp/` file is the right home for `last_import_settle_utc` across domain reloads.
- Whether the observed refresh latency and reload frequency are acceptable on a large project.

The earlier plan to benchmark unconditional refresh is dropped: unconditional refresh was already rejected on the 10s no-change cost and the domain-reload state reset, so measuring it would not change a decision.

## Capabilities

### New Capabilities

- `import-change-refresh`: observe import-triggering project changes from the Editor side and perform `AssetDatabase.Refresh()` before exec when, and only when, a change that needs importing is detected; report why a refresh happened or was skipped.

### Modified Capabilities

- `formal-cli-contract`: `--refresh-before-exec` is documented as a forced-refresh override; refresh activity appears in diagnostics.
- `project-control-endpoint`: health or diagnostics surface refresh state and skip reasons.
- `cache-staleness-detection`: unaffected in contract, but fewer domain reloads means fewer fingerprint resets — worth confirming rather than assuming.

## Impact

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs` — watcher lifecycle, settled-import tracking, refresh decision, dispatched through the existing `MainThreadActions` queue; watcher callbacks must not touch Unity APIs off the main thread.
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecProtocol.cs` — diagnostics fields.
- `cli/python/unity_puer_exec_runtime.py`, `cli/python/help_surface.py` — flag semantics and help text.
- `tests/` — mock coverage for the decision logic; real-host coverage for watcher precision and false-positive rate.

## Discoverability validation

The formal CLI help surface changed (the `--refresh-before-exec` guidance was rewritten and the code-only refresh boundary was added). Per `agent-cli-discoverability-validation`, a help-only agent validation run is a comparison exercise for help-efficiency changes; the change's impact notes record that a help-efficiency evaluation was **not required** for this change, because the help edits remove a now-invalid flag rather than restructure discovery paths, and the behavior they describe is covered by the real-host refresh tests. If a later help-efficiency comparison is run, these sites are the baseline.
