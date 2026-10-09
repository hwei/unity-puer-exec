## 1. One tolerant shared endpoint probe

- [ ] 1.1 List every shared real-host helper and direct probe that assumes a stable endpoint: `_SharedRealHostDevice._base_url` / `_ensure_shared_host_ready`, `RefreshOnChangeRealHostTests._health` / `_wait_for_refresh_pending` / `_wait_for_ready_project`, `PlayModeCompileBlockRealHostTests._health` / `_wait_for_refresh_pending`, and any direct `unity_session._probe_health` call in a case. Classify each as (a) must tolerate a reload window, (b) genuinely requires a live endpoint now, or (c) already tolerant. Verify: every call site is listed with its class and a one-line reason.
- [ ] 1.2 Confirm the endpoint can rebind to a different port across a reload (occupied preferred port), so tolerance must re-resolve and not only retry the same URL. Verify: the finding states whether re-resolution is required on the validation host.
- [ ] 1.3 Add the shared tolerant probe to `_SharedRealHostDevice`: retry transport failures within a bound, re-resolve via `_scan_ready_control_endpoint(self.project_path)`, and return `(base_url, payload)` or raise a named timeout. Verify: a forced `None` probe followed by a ready endpoint returns the ready payload without failing.
- [ ] 1.4 Route `_wait_for_refresh_pending` and the per-class `_health` one-shot probes through the shared probe, keeping a one-shot assertion only for class (b) with an explicit message. Verify: `_health` still fails a case when the endpoint never returns within the bound, with a message naming the reload window.
- [ ] 1.5 Delete the duplicated play-mode/refresh helper copies from the two classes and keep a single definition on the shared device. Verify: the module contains one definition of each helper and both classes still run.
- [ ] 1.6 Exercise a deliberately dropped endpoint mid-wait (staged or unit-mocked). Verify: the regression is deterministic, not only a lucky real-host run.

## 2. Import-safe temp-asset deletion

- [ ] 2.1 Add an Editor-side delete path for declared validation-temp assets (through `exec` / `AssetDatabase.DeleteAsset`), reaching the Editor through the shared probe from 1.3, and use it when a ready control endpoint exists; keep the filesystem delete as the no-Editor fallback. Verify: with the shared Editor live, cleanup removes the roots and the Editor shows no `Opening file failed` modal for a removed `.cs.meta`.
- [ ] 2.2 Remove the ScriptUpdater trigger fixture on the skip path as well as the normal path. Verify: after a skipped ScriptUpdater case, the fixture file and its `.meta` are gone.
- [ ] 2.3 Preserve the declared-inventory limit and the recorded cleanup result. Verify: cleanup still refuses targets outside the declared roots, and still reports `removed` / `residue` / `errors`.

## 3. Per-case scene and modal reset

- [ ] 3.1 Restore the active scene in `_reset_shared_host_state`. Verify: a case that leaves a pathless or unsaved scene does not change which dialog the next save-scene case observes.
- [ ] 3.2 Clear any residual modal, including a dialog outside the catalog, before the next case runs. Verify: a case that stages an unknown modal does not leak it into the next case.
- [ ] 3.3 Make the save-scene dialog cases stage their own scene. Verify: each asserts only the dialog state it set up.

## 4. Validation

- [ ] 4.1 Run the real-host suite. Verify: green, no `Opening file failed` modal is observed, `test_resolve_blocker_cancel_is_rejected_for_save_scene` is stable across repeated runs, the play-mode cases pass without a manual retry, and the run introduces no new helper copy.
- [ ] 4.2 Run the default unit suite and `openspec validate harden-real-host-per-case-reset`. Verify: both green.
