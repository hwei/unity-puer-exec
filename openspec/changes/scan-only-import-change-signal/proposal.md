## Why

`refresh-on-change` shipped with a `FileSystemWatcher` per watched root as an
"accelerator" and an incremental directory scan as the real signal source. The watcher
was measured, not assumed, and the measurement is decisive: Unity Editor's embedded Mono
on Windows delivers **zero** FileSystemWatcher events on startup and only delayed,
unreliable events later — an in-process probe bound the watcher, confirmed it raising,
and recorded no callbacks, while the same watcher outside the editor fired instantly.
The scan is what actually detects every change; that was the point of the fix that closed
the change.

So on the platform this repository targets, the watcher contributes nothing and cannot be
the source of truth. Its costs, however, are real and structural:

- It keeps alive a whole fallback subsystem that exists only because a watcher can fail:
  error-event invalidation, the `signalValid`/`unknown` state, the deferred error
  diagnostic, a one-shot revalidation requirement, and the "signal is an accelerator,
  not the source of truth" framing itself.
- It binds watchers and maintains callback handlers whose threads must be audited for
  Unity-API purity — a contract that had to be enforced by a dedicated source-invariant
  test after diagnostic logging leaked back into the callbacks.
- It anchors two spec requirements and a health contract (`unknown`) about a mechanism
  that never fires. A reading of the specs implies the signal is watcher-backed with a
  scan fallback; the truth is the reverse, and only the scan is load-bearing.

macOS/Linux are explicitly out of scope for this repository, so "the watcher would work
elsewhere" is not a reason to keep a subsystem that does not work here.

## What Changes

- **Delete the `FileSystemWatcher` from the import-change tracker.** The incremental
  directory scan (directory-mtime gated, known-code-file re-stat, per-directory
  snapshot) is the signal, full stop.
- **Delete the watcher fallback subsystem.** Error-event invalidation, the
  `signalValid` / deferred-error state, the candidate set the callbacks fed, and the
  one-shot revalidation rule all go with it. The scan already catches every case the
  fallback existed to cover — pre-attach changes and post-reload changes included,
  because every decision scans the filesystem rather than depending on in-memory event
  state.
- **Simplify the tracker lifecycle.** `Install()` loads the persisted settled-import
  timestamp; the install-time baseline walk becomes redundant when every decision scans,
  and is removed with it.
- **Bring the health pending contract in line.** With no watcher to fail, the refresh
  pending state on a ready service is a plain pending / not-pending, and the `unknown`
  cause named in the spec (watcher error, domain reload resetting watcher state) no
  longer exists.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `import-change-refresh`: change detection is defined as the scan; the requirement that
  the decision "survives watcher failure modes" and the one-shot revalidation
  requirement are removed, replaced by a scan-only detection requirement.
- `project-control-endpoint`: the health pending requirement drops the watcher-related
  `unknown` cause.

## Impact

- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecImportChangeTracker.cs` —
  watcher lifecycle, fallback state, candidate set, and baseline walk removed; the scan
  becomes the sole producer of "changed since the settled import".
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs` — health pending
  mapping loses its `unknown` branch.
- `openspec/specs/import-change-refresh/spec.md`,
  `openspec/specs/project-control-endpoint/spec.md` — spec deltas above.
- `tests/` — the watcher-error real-host case and the watcher source-invariant cases are
  removed or rewritten; the scan cases (`non-code writes`, `baseline/pre-attach`,
  `settled timestamp`, `play mode`) stay and are the regression surface.
- No CLI change and no change to the refresh diagnostics block for the ordinary paths;
  `reason: watcher_signal_unavailable` disappears because nothing can produce it.
