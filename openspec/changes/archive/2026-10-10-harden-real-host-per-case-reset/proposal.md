# Proposal

## Why

While validating `preflight-compile-check-before-editor-launch` and
`surface-play-mode-compile-block`, the real-host suite exposed three harness defects that are
independent of the product changes under test and reproduce without them. This change also
absorbs the former `harden-real-host-endpoint-helpers` change (now superseded): both fix
`tests/test_real_host_integration.py` robustness, both need the same real-host run as
evidence, and the per-case reset added here itself crosses domain reloads.

First, deleting repository-owned validation temp assets from **outside** the Editor races
Unity's asset pipeline. `cleanup_validation_temp_assets()` is a `shutil.rmtree` of
`Assets/__codex_validation_temp`; when a live Editor still references a file under that
directory (the ScriptUpdater fixture's `.cs` / `.cs.meta` is the observed case), Unity tries
to reopen the now-missing `.meta` and shows a modal
`Opening file failed … ScriptUpdaterTriggerFixture.cs.meta: 系统找不到指定的路径`. That modal
can sit in front of subsequent cases.

Second, the per-case reset does not restore the active scene. The scene-dependent save-scene
dialog cases therefore inherit whatever scene state the previous case left. When that state
differs from what the case assumes (a pathless/new scene, or a stray modal already up), the
case observes no catalog dialog and reports `no_supported_blocker` instead of the
`resolution_failed` it asserts. This is the likely cause of the one-off
`test_resolve_blocker_cancel_is_rejected_for_save_scene` failure (1 of 3 runs; the dialog was
visible while the case passed in another run).

Third, the suite assumes the control endpoint is stable between a request and the next probe.
Unity drops that endpoint around every domain reload: a script compile, a play-mode exit with a
deferred compile, and the assembly reload that ends it. A helper that probes once and asserts
fails for a reason unrelated to the behavior under test.
`test_play_mode_skips_refresh_and_preserves_pending_change` failed on `_health()`
`assertIsNotNone` with `[WinError 10054]` immediately after play exit and needed a manually
retried run to pass; `_wait_for_refresh_pending` polls through the same `_health()`. The
tolerant pattern already exists in `_wait_for_play_exit` and `_wait_for_refresh_state`, but is
duplicated across `RefreshOnChangeRealHostTests` and `PlayModeCompileBlockRealHostTests`.

## What Changes

- Make validation temp-asset deletion import-safe: remove the assets through the live
  Editor's own asset pipeline, or otherwise ensure the Editor has released them, instead of
  an out-of-process directory delete. Keep the existing declared-inventory limit and
  per-run result recording.
- Remove the ScriptUpdater fixture on every outcome, including the skip path, so it cannot
  be left behind for a later cleanup to trip over.
- Extend the per-case reset to restore the active scene and to clear a residual modal before
  the next case runs, so a scene-dependent case does not inherit another case's scene state.
- Make the save-scene dialog cases stage their own scene instead of depending on the
  inherited one.
- Add one shared tolerant endpoint probe on `_SharedRealHostDevice`: it retries a transport
  failure within a bound, re-resolves the project's published control-port endpoint, and
  returns the endpoint and payload (or raises a named timeout). The per-case reset and the
  Editor-side cleanup use it.
- Route the single-shot `_health` probes and `_wait_for_refresh_pending` through it. Keep a
  one-shot readiness assertion only where the case genuinely requires an endpoint that is up
  now, and say so in the assertion message.
- De-duplicate the copied play-mode/refresh helpers between `RefreshOnChangeRealHostTests` and
  `PlayModeCompileBlockRealHostTests` onto the shared device.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `validation-temp-asset-cleanup`: cleanup must not remove a validation-temp asset that the
  live Editor's import pipeline still references, and must remove the ScriptUpdater fixture
  on every outcome.
- `validation-host-integration`: per-case reset scope gains the active scene and residual
  modal, so a case does not observe another case's scene state; real-host probes tolerate the
  control endpoint's domain-reload window.

## Impact

- `tests/test_real_host_integration.py`: per-case reset, temp-asset cleanup calls, the
  save-scene dialog cases, the shared device's probe helpers, the per-class duplicates, and
  every case that calls the one-shot `_health`.
- `tools/cleanup_validation_host.py`: deletion path if the fix lives there.
- Possibly a small Editor-side delete entry reached through `exec` (if deletion must run
  inside Unity). No CLI contract change.
- Evidence: real-host suite; the compile preflight is unrelated and already archived.
