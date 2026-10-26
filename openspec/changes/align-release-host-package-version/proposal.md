# Proposal

## Why

`tools/release_openupm.py --real-host-validation` cannot pass across a version bump on any host that loads an embedded copy of the package, and when it fails it says nothing useful about why.

Observed while preparing `v0.12.0` (2026-10-26):

- `python tools/release_openupm.py --version 0.12.0 --commit --tag --real-host-validation` reported `failures=42, skipped=1` out of 43 real-host tests in 6m14s. Every failure was the same line at `setUp`: `version_mismatch: CLI version 0.12.0 does not match the Unity bridge version 0.11.0`.
- The validation host (`c3-client-tree2/Project`) carries an embedded copy at `Project/Packages/com.txcombo.unity-puer-exec/` that declares the formal package name. Unity loads embedded packages ahead of the `file:` dependency `tools/prepare_validation_host.py` writes into `Packages/manifest.json`, so the host ran 0.11.0 code while the CLI reported 0.12.0.
- The helper bumps `packages/com.txcombo.unity-puer-exec/package.json` in this repository only. The CLI's non-frozen version comes from that file (`cli_version.source_tree_version`), while the bridge reports `PackageInfo.FindForAssembly(...).version` of whatever package Unity actually loaded (`UnityPuerExecServer.ResolveBridgeVersion`). A release bump therefore *guarantees* a mismatch whenever the host's loaded copy is a separate directory.
- Editing the host copy's `package.json` to `0.12.0` by hand made the same command pass 43/43 in 39m37s.

So the failure mode is structural, not environmental: the single step that can make real-host validation meaningful (host copy carries the release candidate version) is manual, undiscovered until after a 35-minute suite run, and reported as 42 unrelated stack traces. The mismatch also silently invalidates the evidence in the other direction: had the host copy simply been stamped to 0.12.0 while still holding stale code, the suite would have passed while validating old code.

## What Changes

- **Host package identity preflight.** Before `--real-host-validation` runs anything, the helper resolves the validation host, finds the package tree Unity will actually load (reusing `prepare_validation_host.detect_embedded_package_shadowing`), reads that tree's `package.json` version, and compares it with the release candidate version. A mismatch stops release preparation before any Editor launch or test execution, with one structured error naming the loaded package path, the expected version, the observed version, and the two remedies.
- **Opt-in version alignment.** A new `--sync-host-version` option stamps the release candidate version into the loaded host copy's `package.json`, but only when that copy's package files match this repository's package tree. Parity is checked over the release-relevant tree (`Editor/`, `Tests/`, root files) while ignoring the version field itself and the host copy's published `CLI~/` binaries. Divergence refuses with `host_package_stale` naming the differing paths instead of stamping a version onto code that would validate old behavior.
- **Rollback restores the host.** If release preparation fails after alignment (unit suite, real-host suite, commit, or tag), the helper restores the host copy's original `package.json` bytes, so the host stays consistent with the repository version that is left behind.
- **Machine-readable surface.** The preflight outcome (loaded path, observed version, parity verdict, whether a write would happen or did) appears in the helper's JSON result, including under `--dry-run`, which reports it without touching the host.

Not changed: `--real-host-validation` stays opt-in; the file-based wiring path (`prepare_validation_host.py`) keeps its contract; the remedy of removing an embedded copy entirely stays valid and documented; the helper still never pushes.

## Why not simply delete the embedded copy

Removing the shadowing directory is the documented way to make the `file:` dependency win, but on this workspace the host copy is operator-managed, git-tracked, and carries the published `CLI~/unity-puer-exec.exe`. Deleting another repository's working state is not a release helper's decision, and it would also erase the only place a real installed-CLI run can be exercised. The helper diagnoses and, when explicitly asked, aligns the version identity only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `openupm-release-helper`: `--real-host-validation` gains a host package identity prerequisite, an opt-in alignment step, and rollback of that alignment.
- `validation-host-integration`: the run instructions state that a host loading an embedded copy must carry the release candidate version, and how the helper reports or aligns it.

## Impact

- Tooling: `tools/release_openupm.py` (preflight, new option, rollback restore, JSON surface); small new helpers for locating the host-loaded package tree and comparing package trees, kept importable by tests.
- Docs: `openspec/specs/openupm-release-pipeline/how-to-run.md`, `openspec/specs/validation-host-integration/how-to-run.md`.
- Tests: `tests/test_release_openupm_tool.py` gains fixtures that build a fake host in a temporary directory (embedded copy present / absent, matching / stale), plus dry-run, refusal, alignment, and rollback cases. No Editor is required for any of them.
- Compatibility: hosts wired purely through the `file:` dependency are unaffected — the loaded tree *is* the repository package, so the preflight passes without any write. The new option is additive; default behaviour for a mismatched host changes from "run 43 tests and fail" to "stop with one diagnosis".
