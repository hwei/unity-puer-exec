# Tasks

## 1. Host package identity resolution

- [ ] 1.1 Add a helper that resolves the host project the same way the real-host suite does (`--project-path`, then `UNITY_PROJECT_PATH`, then `.env`) and classifies the loaded package tree: embedded (single match by declared `name`), file-dependency, ambiguous (two or more embedded matches), or not wired. Reuse `prepare_validation_host.detect_embedded_package_shadowing` rather than re-implementing detection.
- [ ] 1.2 Read the loaded tree's declared version and compare it with the candidate version, returning a structured verdict (`loaded_via`, `loaded_root`, `observed_version`, `expected_version`) plus a refusal code per case: `host_package_version_mismatch`, `host_package_ambiguous`, `host_package_not_wired`.
- [ ] 1.3 Compare against a reachable live control endpoint for the host when one exists: a `bridge_version` differing from an on-disk matching version refuses as `host_editor_stale` with a restart remedy. Confirm the probe never launches or restarts anything.

## 2. Release helper integration

- [ ] 2.1 Run the preflight whenever `--real-host-validation` is requested, before the unit suite, and stop on any refusal without invoking either test command. Keep hosts wired only through `file:` on the success path with no host write.
- [ ] 2.2 Add `--sync-host-version`, accepted only together with `--real-host-validation`; without it, a mismatch is a refusal rather than a write.
- [ ] 2.3 Implement the parity gate over `Editor/`, `Tests/`, and package root files (`README.md`, `LICENSE`, `package.json`, `*.meta`), ignoring the `version` field and `CLI~/`; on divergence refuse as `host_package_stale` and name a bounded list of differing paths.
- [ ] 2.4 Write only the `version` field, preserving every other byte of the host `package.json`; capture the original bytes first.
- [ ] 2.5 Extend the existing rollback path to restore the host `package.json` original bytes whenever repository version restore happens, and to leave the alignment in place once the release commit exists.
- [ ] 2.6 Surface the preflight in the helper's JSON result (`real_host_validation.host_package`) for both real runs and `--dry-run`, and list alignment in `planned_actions` / `executed_actions`. Dry run reports the verdict and writes nothing.

## 3. Tests

- [ ] 3.1 Add temporary-directory host fixtures to `tests/test_release_openupm_tool.py`: embedded copy matching, embedded copy with version-only drift, embedded copy with code drift, no embedded copy plus `file:` manifest entry, no wiring at all, and two embedded copies.
- [ ] 3.2 Cover the refusal matrix: each refusal code, its message content (paths and versions), and that neither the unit suite nor the real-host suite ran.
- [ ] 3.3 Cover alignment: version-only write with byte preservation, `--sync-host-version` required, parity refusal names the differing paths and writes nothing, and alignment is not attempted without real-host validation.
- [ ] 3.4 Cover rollback: a failing suite after alignment restores both the host bytes and the repository version; a successful preparation keeps the aligned host version.
- [ ] 3.5 Cover dry run: reports loaded path, both versions and the parity verdict, and leaves the host `package.json` unchanged.

## 4. Documentation

- [ ] 4.1 Update `openspec/specs/openupm-release-pipeline/how-to-run.md` with the host identity prerequisite, `--sync-host-version`, the refusal codes, and the running-Editor caveat.
- [ ] 4.2 Update `openspec/specs/validation-host-integration/how-to-run.md` to state the release-time rule for a host loading an embedded copy, and that a `file:`-wired host needs no action.
- [ ] 4.3 Run the default unit suite and the spec-hygiene test; confirm `python tools/release_openupm.py --version <candidate> --dry-run --real-host-validation` reports the host identity without touching the host.

## 5. Real-host confirmation

- [ ] 5.1 Against the current validation host, temporarily set the embedded copy's version back one release and confirm the helper refuses with a single `host_package_version_mismatch` in seconds, with no Editor launch and no suite run.
- [ ] 5.2 Confirm the aligned path still passes real-host validation end to end at the next release.
