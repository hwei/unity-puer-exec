# Design

## Context

Two independent version sources must agree before real-host validation means anything:

| Side | Source | Code |
| --- | --- | --- |
| CLI | `packages/com.txcombo.unity-puer-exec/package.json` in this repository, for a non-frozen invocation | `cli_version.source_tree_version` |
| Bridge | `PackageInfo.FindForAssembly(...)` of the package Unity actually loaded in the host project | `UnityPuerExecServer.ResolveBridgeVersion` |

`tools/release_openupm.py` writes only the first. The host project's loaded package is decided by Unity's resolution order, not by this repository:

1. An immediate child of the host's `Packages/` whose `package.json` declares `com.txcombo.unity-puer-exec` wins (embedded package, identified by declared `name`, not directory name).
2. Otherwise the `file:` dependency in `Packages/manifest.json` wins. When it was written by `tools/prepare_validation_host.py` that path *is* the repository package.

In case 2 with the repository package, the two versions are equal by construction and a release bump needs no host action. In case 1 they are equal only if someone stamped the host copy — and nothing told the maintainer to, until 43 tests failed.

On the current validation host (`c3-client-tree2/Project`) both are present: the manifest carries the `file:` dependency, but an embedded copy shadows it. The operator keeps that copy in sync by copying this repository's package tree into it by hand; at the time of writing it is byte-identical to the repository package apart from `CLI~/`. The mismatch arises because that copy is taken before the release bump, not because its code is stale.

## Decision

The helper owns *identity*, not *content*:

- It refuses to run real-host validation when the host the suite will use cannot be resolved, or when the host's loaded package is not the release candidate.
- When explicitly asked (`--sync-host-version`), it stamps the version into the host's loaded copy, but only after proving that copy's package content equals this repository's package content.
- It restores the host's original bytes if release preparation rolls back, including on interruption.

## Preflight placement

The preflight is read-only and runs whenever `--real-host-validation` is requested, after the existing argument, worktree, tag, and current-version checks and **before** both the `--dry-run` early return and `write_package_version`. Consequences:

- A refusal leaves nothing to roll back: neither the repository nor the host has been written.
- A broken host costs seconds instead of a 35-minute suite run.
- `--dry-run` reports the same verdict a real run would act on.

Because the preflight runs before the repository bump, it must never infer the candidate's identity by reading the repository's `package.json` (that still holds the current version). Identity for the repository package is decided by path, below.

## Preflight algorithm

1. **Resolve the host exactly as the suite does.** Call `prepare_validation_host.resolve_project_path()` with no argument — the same call `tests/test_real_host_integration._require_real_host_project_path` makes (process `UNITY_PROJECT_PATH`, then `.env`). The helper does not gain a `--project-path` option: the suite cannot receive one, so a helper-only override would let the preflight inspect a different host from the one the suite runs against.
2. **Require the host the suite would require.** If the path is unresolvable, the directory does not exist, or `Packages/manifest.json` is missing, refuse `host_project_unavailable`. Today the suite turns each of these into a class-level `SkipTest`, `unittest` exits 0, and the helper records "Ran opt-in real-host validation" although nothing ran. A maintainer who passed `--real-host-validation` asked for evidence, so absence is a refusal, not a skip.
3. **Locate the loaded tree.**
   - Collect immediate children of `<host>/Packages/` that declare the formal package name (reuse `prepare_validation_host.detect_embedded_package_shadowing`, which already excludes a child that resolves to the repository package root).
   - One match → `loaded_root = that child`, `loaded_via = "embedded"`.
   - More than one match → refuse `host_package_ambiguous` naming every path. Unity loads one of them and the helper will not guess which.
   - No match, and the manifest declares the formal name with a `file:` value → resolve that value to a directory, `loaded_via = "file"`. Both written forms must parse: relative to `<host>/Packages/` (`file:../../..`) and absolute (`file:///F:/...`), the two forms `compute_file_dependency` produces.
   - No match and no `file:` entry (absent, or a registry/git version) → refuse `host_package_not_wired` instead of validating a published build.
4. **Decide identity.**
   - `loaded_via = "file"` and the resolved path equals this repository's package root (compared after `resolve()`, case-insensitively on Windows) → identical by construction; `host_package.ok = true`, `identity = "repository_package"`, no version read, no write. This is the only correct answer while the repository bump has not happened yet.
   - Any other loaded tree → read `<loaded_root>/package.json` version as `observed_version` and compare with the candidate version. Equal → `ok = true`. Different → `host_package_version_mismatch`; with `--sync-host-version` continue to alignment, otherwise refuse with the loaded path, both versions, and the two remedies (align with `--sync-host-version`, or remove the embedded copy so the `file:` dependency wins).

No live control endpoint is probed. The real-host suite's `setUpClass` already runs `ensure-closed` on the host before launching a fresh Editor, so an Editor that was open before the release run cannot be what the suite validates. Refusing because such an Editor still reports the old `bridge_version` would block runs that would pass, and is guaranteed to fire right after an alignment. A side effect worth stating in the run instructions: writing `package.json` into the loaded copy while an Editor is open makes that Editor re-resolve packages; the suite then closes it anyway.

## Alignment and parity

Alignment writes one field: `version` in `<loaded_root>/package.json`. It is gated on parity because a stamped version is a claim that this code is the release candidate.

Parity compares `<loaded_root>` with `<repo>/packages/com.txcombo.unity-puer-exec` over the **whole tree, minus a deny list**:

- Exclude `CLI~/` entirely: the host copy carries a published `unity-puer-exec.exe`, the repository ignores its locally built one, and neither is package content under validation.
- Compare the set of relative file paths; any file present on only one side is a difference. An allow list (`Editor/`, `Tests/`, root files) would silently ignore a directory the repository adds later, such as `Runtime/` or `Documentation~/`.
- Compare `package.json` as parsed JSON with the `version` key removed (it is the field being aligned).
- Compare other files after normalising line endings (`\r\n` → `\n`) for content that decodes as UTF-8; compare raw bytes otherwise. The host is a separate git repository with `core.autocrlf` behaviour that rewrites LF to CRLF on checkout; a byte-exact comparison would report every source file as stale after the operator commits and re-checks-out an otherwise identical copy.

Divergence → refuse `host_package_stale` with the differing paths (bounded list, plus a total count) and the remedy: sync the host copy from this repository, or drop the embedded copy and let the `file:` dependency win.

On `--dry-run`, parity is evaluated when `--sync-host-version` is passed so the report can say whether a write *would* be allowed, but nothing is written.

The write replaces only the `version` value in the file's text, preserving every other byte (indentation, key order, line endings, trailing newline). It does not reuse `write_package_version`, which re-serialises the whole document.

## Rollback

The helper already restores the repository `package.json` when preparation fails before the release commit. Alignment extends that transaction:

- Capture the host `package.json` bytes before writing.
- Write the host before the repository bump. If the host write fails, fail the run before anything else changes.
- On any failure before the release commit, restore both the repository version and the host's captured bytes. "Any failure" includes `KeyboardInterrupt` and other `BaseException`s, not only `ReleaseError`: the real-host suite runs for over half an hour, and interrupting it is the most likely way a run ends early. The handler restores and then re-raises.
- Once the release commit is created the alignment stays: the host copy should keep tracking the released version.

## Considered alternatives

| Alternative | Why not |
| --- | --- |
| Fail fast only, never mutate the host | Every release across a bump then needs a manual edit in a second repository. Kept as the default, but not the only path. |
| Delete or move the embedded copy so `file:` wins | Mutates operator-managed host state in another repo and destroys the only place an installed-CLI run can be exercised. The run instructions already offer this as a manual remedy. |
| Copy the whole package tree into the host automatically | Makes release tooling responsible for host content, and a silent copy can mask a host the operator believes mirrors `main`. Identity stamping plus a parity guard keeps the helper's claim narrow. |
| Stamp the version unconditionally when asked | Validating stale code under a new version number is worse than failing: it produces green evidence for the wrong build. Hence the parity gate. |
| Refuse when a live Editor reports an older `bridge_version` | The suite closes and relaunches the Editor itself, so the refusal would only block runs that would pass. |
| Add `--project-path` to the helper | The suite resolves the host only from the environment; an override the suite does not see splits the checked host from the tested host. Passing it through as `UNITY_PROJECT_PATH` would work but adds surface with no current need. |
| Detect the mismatch from the test failure text instead of preflighting | Costs a full suite run (~35 min) and surfaces as 42 stack traces; the same probe is cheap before launch. |

## Failure modes this leaves in place

- The suite can still skip at class level when no Unity Editor executable is resolvable for the host (`_require_unity_editor`), and the helper would still record the suite as run. The preflight covers host resolution only; Editor-executable resolution stays with the suite.
- A maintainer who edits the host copy between preflight and suite execution: unreachable in one release run because both happen in the same helper invocation.

## Test strategy

All cases are mockable without Unity:

- Fake hosts built in temporary directories: embedded copy present (matching / version-only drift / code drift / CRLF-only drift / extra file in a new top-level directory), absent with a relative `file:` entry pointing at a fake repository package root, absent with an absolute `file:///` entry, absent with a `file:` entry pointing elsewhere, absent with no entry, two embedded copies declaring the name, and an unresolvable or missing host.
- The `file:`-to-repository case runs while the repository `package.json` still holds the current version, and must pass with no version read and no write.
- Assert refusal codes and that no unit or real-host test command is invoked on refusal (patch the test runner, assert zero calls), and that the repository `package.json` was never written.
- Assert dry-run reports the identity and alignment verdict and writes nothing.
- Assert alignment writes only the version value and preserves the rest of the file byte-for-byte, including CRLF line endings.
- Assert failure after alignment — a `ReleaseError` and a `KeyboardInterrupt` raised from the patched suite runner — restores the original host bytes and the original repository version and re-raises.

Real-host confirmation does not wait for a release: one refusal run against a deliberately lagging host copy, and one aligned end-to-end run without `--commit` whose bump is then reverted by hand (see tasks).
