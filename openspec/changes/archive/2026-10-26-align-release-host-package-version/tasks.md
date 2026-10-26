# Tasks

## 1. Host package identity resolution

- [x] 1.1 Add a helper that resolves the host project with `prepare_validation_host.resolve_project_path()` called exactly as the real-host suite calls it (no argument; process `UNITY_PROJECT_PATH`, then `.env`). Do not add a `--project-path` option to the release helper. Refuse `host_project_unavailable` when the path is unresolvable, the directory is missing, or `Packages/manifest.json` is missing — the same conditions the suite turns into a silent class-level skip.
- [x] 1.2 Classify the loaded package tree: embedded (single match by declared `name`), file-dependency, ambiguous (two or more embedded matches), or not wired (no `file:` entry, including registry/git versions). Reuse `prepare_validation_host.detect_embedded_package_shadowing` rather than re-implementing detection. Parse both `file:` forms `compute_file_dependency` writes: relative to `<host>/Packages/` and absolute `file:///`.
- [x] 1.3 Decide identity: a `file:` path that resolves to this repository's package root (after `resolve()`, case-insensitive on Windows) is identical by construction — no version read, no write. Otherwise read the loaded tree's declared version and compare with the candidate version. Return a structured verdict (`loaded_via`, `loaded_root`, `identity`, `observed_version`, `expected_version`) plus a refusal code per case: `host_project_unavailable`, `host_package_ambiguous`, `host_package_not_wired`, `host_package_version_mismatch`. No live control endpoint is probed.

## 2. Release helper integration

- [x] 2.1 Run the preflight whenever `--real-host-validation` is requested, after the existing argument / worktree / tag / current-version checks and before both the `--dry-run` return and `write_package_version`. On any refusal stop without writing the repository or the host and without invoking either test command.
- [x] 2.2 Add `--sync-host-version`, accepted only together with `--real-host-validation`; without it, a mismatch is a refusal rather than a write.
- [x] 2.3 Implement the parity gate over the whole package tree minus `CLI~/`: compare relative path sets; compare `package.json` as parsed JSON without the `version` key; compare UTF-8 files after `\r\n` → `\n` normalisation and other files as raw bytes. On divergence refuse as `host_package_stale`, naming a bounded list of differing paths and the total count.
- [x] 2.4 Capture the host `package.json` bytes, then replace only the `version` value in its text, preserving every other byte (do not reuse `write_package_version`). Perform the host write before the repository bump; a failed host write ends the run before anything else changes.
- [x] 2.5 Extend the rollback path so that any exception before the release commit — `ReleaseError`, `KeyboardInterrupt`, or other `BaseException` — restores both the repository version and the host's captured bytes, then re-raises. Leave the alignment in place once the release commit exists.
- [x] 2.6 Surface the preflight in the helper's JSON result (`real_host_validation.host_package`) for both real runs and `--dry-run`, and list alignment in `planned_actions` / `executed_actions`. Dry run reports the identity verdict, and the parity verdict when `--sync-host-version` is passed, and writes nothing.

## 3. Tests

- [x] 3.1 Add temporary-directory host fixtures to `tests/test_release_openupm_tool.py`: embedded copy matching, version-only drift, code drift, CRLF-only drift, extra file in a new top-level directory; no embedded copy with a relative `file:` entry to a fake repository package root, with an absolute `file:///` entry, and with a `file:` entry pointing elsewhere; no wiring at all; two embedded copies; unresolvable host and host missing its manifest.
- [x] 3.2 Cover the `file:`-to-repository case while the repository `package.json` still holds the current version: the preflight passes with no version read and no host write.
- [x] 3.3 Cover the refusal matrix: each refusal code, its message content (paths and versions), that neither the unit suite nor the real-host suite ran, and that the repository `package.json` was not written.
- [x] 3.4 Cover alignment: version-only write with byte preservation (including CRLF files), `--sync-host-version` required, CRLF-only drift passes parity, a new-directory file fails parity, parity refusal names the differing paths and writes nothing, and alignment is not attempted without real-host validation.
- [x] 3.5 Cover rollback: a `ReleaseError` and a `KeyboardInterrupt` from the patched suite runner each restore both the host bytes and the repository version and re-raise; a successful preparation keeps the aligned host version.
- [x] 3.6 Cover dry run: reports loaded path, identity, both versions and the parity verdict, and leaves the host and repository `package.json` unchanged.

## 4. Documentation

- [x] 4.1 Update `openspec/specs/openupm-release-pipeline/how-to-run.md` with the host identity prerequisite, `--sync-host-version`, the refusal codes (including `host_project_unavailable` replacing the former silent skip), and that writing the host `package.json` makes an open Editor re-resolve packages while the suite relaunches the Editor regardless.
- [x] 4.2 Update `openspec/specs/validation-host-integration/how-to-run.md` to state the release-time rule for a host loading an embedded copy, that parity ignores `CLI~/` and line-ending differences, and that a `file:`-wired host pointing at this repository needs no action.
- [x] 4.3 Run the default unit suite and the spec-hygiene test; confirm `python tools/release_openupm.py --version <candidate> --dry-run --real-host-validation` reports the host identity without touching the host or the repository.

## 5. Real-host confirmation

- [x] 5.1 Against the current validation host, record the embedded copy's `package.json` bytes, set its version back one release, and confirm the helper refuses with a single `host_package_version_mismatch` in seconds, with no Editor launch, no suite run, and no repository write. Put the recorded bytes back.
- [x] 5.2 Confirm the aligned path end to end without waiting for a release: record the host `package.json` bytes, run `python tools/release_openupm.py --version <next> --real-host-validation --sync-host-version` without `--commit`, and confirm both suites pass. Then revert by hand — `git restore` the repository `package.json`, and write the recorded bytes back to the host `package.json`. Do not `git restore` the host copy: its working tree carries operator-synced package content that is not committed in the host repository.
