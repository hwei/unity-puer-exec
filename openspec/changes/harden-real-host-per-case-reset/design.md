# Design

## Context

See proposal.md — Why. Relevant current state:

- `tools/cleanup_validation_host.py` `cleanup_validation_temp_assets(project_path)` is an
  out-of-process `shutil.rmtree` over the declared validation-temp roots and their `.meta`
  siblings. It is called from the real-host `setUpClass`, `setUp`, `tearDownClass`, and the
  ScriptUpdater case's `finally`.
- The shared Editor is alive for the whole suite (one Editor per class), so a cleanup almost
  always runs while Unity still references assets under `Assets/__codex_validation_temp`.
- `_reset_shared_host_state()` already resets temp assets, residual modals, play mode, compile
  state, and the change signal, but not the active scene.
- The save-scene dialog cases call `MarkSceneDirty` + `SaveCurrentModifiedScenesIfUserWantsTo()`
  and assume the active scene yields Unity's standard save dialog.
- `RefreshOnChangeRealHostTests._health` / `_wait_for_refresh_pending` and
  `PlayModeCompileBlockRealHostTests._health` / `_wait_for_refresh_pending` probe the endpoint
  once per call and treat a `None` payload as a failure. `_wait_for_play_exit` and
  `_wait_for_refresh_state` already tolerate the reload window, in two per-class copies.
- The endpoint can rebind to a different port across a reload when the preferred port is
  occupied (`harden-control-port-rollover-validation`), so tolerance has to re-resolve the
  endpoint, not only retry the same URL.

## Goals / Non-Goals

**Goals:**
- Remove validation temp assets without leaving the Editor opening a deleted `.cs`/`.cs.meta`.
- Make scene-dependent cases independent of the previous case's scene.
- Keep the declared-inventory limit and the recorded cleanup outcome.
- Make every endpoint probe in the suite survive a domain reload, with one shared helper.

**Non-Goals:**
- Changing the CLI contract, the control endpoint, or the compile preflight.
- Building a general-purpose remote asset-deletion API.
- Any change to `cli/` or `packages/` for endpoint tolerance; it is harness-only.

## Decisions

### D1. Delete temp assets through the live Editor, not around it

When the project has a ready control endpoint, remove the assets with
`AssetDatabase.DeleteAsset` executed through the existing `exec` path, so Unity's asset
database and the filesystem change together and the import pipeline never looks for a
vanished `.meta`. When no live Editor is present, the current filesystem delete is already
safe and is kept as the fallback.

Alternatives considered: a fixed sleep before `rmtree` (time-based, racy, and slow); disabling
ScriptUpdater (side effect on the product under validation). Rejected.

### D2. Remove the ScriptUpdater fixture on every outcome

The ScriptUpdater case already restores its fixture in a `finally`; the skip path must run the
same removal so a skipped case cannot be the one that leaves a still-referenced fixture behind.
This is a correctness fix to the case, independent of D1.

### D3. Extend the per-case reset to the scene and to any residual modal

The reset restores the active scene to a stable state (the project's default scene, or a
freshly saved empty scene) before each case, and clears any residual modal — catalog or
unknown — so a scene-dependent case cannot inherit a pathless/new scene or a stale dialog.
Scene-dependent cases additionally stage their own scene, so they assert only what they set up.

### D4. One tolerant shared endpoint probe

`_SharedRealHostDevice` gains one probe that retries transport failures within a bound,
re-resolves through `_scan_ready_control_endpoint(self.project_path)`, and returns
`(base_url, payload)` or raises a named timeout that names the reload window. The per-class
`_health`, `_wait_for_refresh_pending`, `_wait_for_play_exit`, and `_wait_for_refresh_state`
move onto the shared device on top of it. D1 and D3 reach the Editor through `exec` right after
cases that reload the domain, so they use this probe to find a live endpoint first; it is built
first for that reason.

Call sites are classified before routing: (a) must tolerate a reload window, (b) genuinely
requires a live endpoint now, (c) already tolerant. Only (b) keeps a one-shot assertion, with a
message that says why.

## Risks / Trade-offs

- [An `exec`-based delete adds a round-trip per cleanup] → Only issued when the declared roots
  actually contain files; most cases have none.
- [The default scene may itself change what a case sees] → Cases that care stage their own
  scene (D3), so the reset only needs to guarantee "not the previous case's scene".
- [A failed Editor-side delete silently leaves residue] → The existing cleanup result is still
  computed and recorded after the attempt.
- [A tolerant probe hides a real endpoint failure] → The retry is bounded, and the timeout
  fails the case with a message naming the reload window, so a never-returning endpoint still
  fails.

## Migration Plan

Not applicable — a harness/test change; no product or data migration.

## Open Questions

- Whether the Editor-side delete belongs in `tools/cleanup_validation_host.py` (taking a
  base URL) or in the real-host reset that already resolves the endpoint. This is an
  implementation placement detail that does not change the specs or the approach.
