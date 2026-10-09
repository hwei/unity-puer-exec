## 1. Import-safe temp-asset deletion

- [ ] 1.1 Add an Editor-side delete path for declared validation-temp assets (through `exec` / `AssetDatabase.DeleteAsset`) and use it when a ready control endpoint exists, keeping the filesystem delete as the no-Editor fallback. Verify: with the shared Editor live, cleanup removes the roots and the Editor shows no `Opening file failed` modal for a removed `.cs.meta`.
- [ ] 1.2 Remove the ScriptUpdater trigger fixture on the skip path as well as the normal path. Verify: after a skipped ScriptUpdater case, the fixture file and its `.meta` are gone.
- [ ] 1.3 Preserve the declared-inventory limit and the recorded cleanup result. Verify: cleanup still refuses targets outside the declared roots, and still reports `removed` / `residue` / `errors`.

## 2. Per-case scene and modal reset

- [ ] 2.1 Restore the active scene in `_reset_shared_host_state`. Verify: a case that leaves a pathless or unsaved scene does not change which dialog the next save-scene case observes.
- [ ] 2.2 Clear any residual modal, including a dialog outside the catalog, before the next case runs. Verify: a case that stages an unknown modal does not leak it into the next case.
- [ ] 2.3 Make the save-scene dialog cases stage their own scene. Verify: each asserts only the dialog state it set up.

## 3. Validation

- [ ] 3.1 Run the real-host suite. Verify: green, no `Opening file failed` modal is observed, and `test_resolve_blocker_cancel_is_rejected_for_save_scene` is stable across repeated runs.
- [ ] 3.2 Run the default unit suite and `openspec validate harden-real-host-per-case-reset`. Verify: both green.
