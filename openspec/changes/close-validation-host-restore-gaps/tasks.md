# Tasks

## 1. Backup on first manifest write

- [ ] 1.1 In `tools/prepare_validation_host.py`, add the `.unity-puer-exec-manifest-backup/` root. Before `write_manifest` writes, save the original `manifest.json` and `packages-lock.json` (when present) if no backup exists yet, and always update `written-manifest.sha256`. Add `manifest_backup_path` to the report. Dry-run writes nothing. Verify with new cases in `tests/test_prepare_validation_host_tool.py`: first write creates the backup; a second write keeps the originals and refreshes the hash; dry-run creates nothing

## 2. `--restore-manifest` operation

- [ ] 2.1 Add `restore_manifest(project_path, manifest_path=..., dry_run=...)` that returns the shared outcome envelope. It refuses through `host_freedom_refusal`, refuses with `manifest_modified_since_prepare` on a hash mismatch, reports `unchanged` when no backup exists, moves the originals back, removes the sidecar and the empty root, and reports `left_in_place` when no original lock file existed. Wire it into the mutually exclusive group and the shared `main()` branch, and add the flag help text. Verify with tool tests for each spec scenario: restore, unchanged, foreign-edit refusal, regenerated-lock proceeds, live-Editor refusal, dry-run preview, and exit code 2 on refusal
- [ ] 2.2 Update `openspec/specs/validation-host-integration/how-to-run.md`: add a teardown step that runs `python tools/prepare_validation_host.py --restore-manifest` after the Editor is closed, alongside `--restore-embedded-shadow`, and document the refusal reasons. Verify that the documented commands match `--help` output

## 3. Release helper hint

- [ ] 3.1 Update the `host_package_version_mismatch` and `host_package_stale` messages in `tools/release_openupm.py` per design D5. Verify with assertions in `tests/test_release_openupm_tool.py` that both messages contain `--clear-embedded-shadow` and `--restore-embedded-shadow`, and that `host_package_version_mismatch` still contains `--sync-host-version`

## 4. Integration check

- [ ] 4.1 Run the full mocked suite listed in how-to-run.md and confirm it is green. Run `openspec validate close-validation-host-restore-gaps --strict` and confirm it passes

## Workflow follow-up

- On the next real-host session, use `--restore-manifest` as the teardown instead of a manual `git checkout`, and note the outcome in that session's closeout.
- Apply closeout per AGENTS.md, then `git commit`, `openspec archive close-validation-host-restore-gaps`, and the final `git commit` when the human asks.
