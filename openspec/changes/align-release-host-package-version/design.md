# Design

## Context

Two independent version sources must agree before real-host validation means anything:

| Side | Source | Code |
| --- | --- | --- |
| CLI | `packages/com.txcombo.unity-puer-exec/package.json` in this repository, for a non-frozen invocation | `cli_version.source_tree_version` |
| Bridge | `PackageInfo.FindForAssembly(...)` of the package Unity actually loaded in the host project | `UnityPuerExecServer.ResolveBridgeVersion` |

`tools/release_openupm.py` writes only the first. The host project's loaded package is decided by Unity's resolution order, not by this repository:

1. An immediate child of the host's `Packages/` whose `package.json` declares `com.txcombo.unity-puer-exec` wins (embedded package, identified by declared `name`, not directory name).
2. Otherwise the `file:` dependency that `tools/prepare_validation_host.py` writes into `Packages/manifest.json` wins, and that path *is* the repository package.

In case 2 the two versions are equal by construction and a release bump needs no host action. In case 1 they are equal only if someone stamped the host copy — and nothing told the maintainer to, until 43 tests failed.

## Decision

The helper owns *identity*, not *content*:

- It refuses to run real-host validation when the host's loaded package version is not the release candidate version.
- When explicitly asked (`--sync-host-version`), it stamps the version into the host's loaded copy, but only after proving that copy's package content equals this repository's package content.
- It restores the host's original bytes if release preparation rolls back.

## Preflight algorithm

Runs whenever `--real-host-validation` is requested, before the unit suite executes (so a broken host costs seconds, not 35 minutes), and under `--dry-run` in report-only mode.

1. Resolve the host project: `--project-path` argument if present, else `UNITY_PROJECT_PATH`, else `.env` — the same precedence `resolve_project_path` and the real-host suite already use. No host resolvable → `host_package.skipped = "no_host"`, and real-host validation keeps its existing skip behaviour.
2. Locate the loaded tree:
   - Collect immediate children of `<host>/Packages/` that declare the formal package name (reuse `prepare_validation_host.detect_embedded_package_shadowing`).
   - One match → `loaded_root = that child`, `loaded_via = "embedded"`.
   - No match, manifest declares the formal name with a `file:` value → `loaded_root = resolved path`, `loaded_via = "file"`.
   - More than one match → refuse `host_package_ambiguous` naming every path. Unity loads one of them and the helper will not guess which.
   - No match and no usable manifest entry → refuse `host_package_not_wired`.
3. Read `<loaded_root>/package.json` version → `observed_version`. Compare with the candidate version.
4. If a live control endpoint for the host is discoverable, also compare its reported `bridge_version` with the candidate version. A live endpoint disagreeing while the file agrees means a running Editor predates the stamp; refuse with `host_editor_stale` (`restart the host Editor`) rather than aligning files that the running process already ignored. Live probing never launches anything.
5. Verdict:
   - versions equal on both sides → `host_package.ok = true`, no action.
   - equal on disk, live endpoint stale → `host_editor_stale`.
   - differ on disk → `host_package_version_mismatch`; if `--sync-host-version` was passed, continue to alignment, otherwise refuse.

## Alignment and parity

Alignment writes one field: `version` in `<loaded_root>/package.json`. It is gated on parity because a stamped version is a claim that this code is the release candidate.

Parity compares `<loaded_root>` with `<repo>/packages/com.txcombo.unity-puer-exec` over the release-relevant tree:

- Compare relative path sets and content hashes for `Editor/`, `Tests/`, and the package root files (`README.md`, `LICENSE`, `package.json`, `*.meta`).
- Ignore the `version` value inside `package.json` (it is the field being aligned).
- Ignore `CLI~/` entirely: the host copy carries a published `unity-puer-exec.exe` that this repository does not track, and its presence is the point of a host copy, not drift.

Divergence → refuse `host_package_stale` with the differing paths (bounded list) and the remedy: sync the host copy from this repository, or drop the embedded copy and let the `file:` dependency win.

On `--dry-run`, parity is still evaluated so the report can say whether a write *would* be allowed, but nothing is written.

## Rollback

The helper already restores `package.json` when preparation fails before the release commit. Alignment extends that transaction:

- Capture the host `package.json` bytes before writing.
- On any failure path, or when preparation rolls back the repository version, write the captured bytes back.
- If the host write itself fails, fail the run before any test executes; the repository edit is restored by the existing rollback path.
- Once the release commit is created the alignment stays: the host copy should keep tracking the released version.

## Considered alternatives

| Alternative | Why not |
| --- | --- |
| Fail fast only, never mutate the host | Every release across a bump then needs a manual edit in a second repository, from an error the maintainer only sees after the fact. Kept as the default, but not the only path. |
| Delete or move the embedded copy so `file:` wins | Mutates operator-managed host state in another repo and destroys the only place an installed-CLI run can be exercised. The run instructions already offer this as a manual remedy. |
| Copy the whole package tree into the host automatically | Makes release tooling responsible for host content, and a silent copy can mask a host the operator believes mirrors `main`. Identity stamping plus a parity guard keeps the helper's claim narrow. |
| Stamp the version unconditionally when asked | Validating stale code under a new version number is worse than failing: it produces green evidence for the wrong build. Hence the parity gate. |
| Detect the mismatch from the test failure text instead of preflighting | Costs a full suite run (~35 min) and surfaces as 42 stack traces; the same probe is cheap before launch. |

## Failure modes this leaves in place

- A host copy whose code matches but whose Unity `Library/` cache still resolves an older package: covered by the live-endpoint comparison when an Editor is running, and by fresh launches otherwise.
- A maintainer who edits the host copy between preflight and suite execution: unreachable in one release run because both happen in the same helper invocation.
- A host wired through a registry version rather than `file:` or embedded: refused as `host_package_not_wired` instead of silently validating a published build.

## Test strategy

All cases are mockable without Unity:

- Fake hosts built in temporary directories: embedded copy present (matching / version-only drift / code drift), absent with a `file:` manifest entry, absent with no entry, two embedded copies declaring the name.
- Assert refusal codes and that no unit or real-host test command is invoked on refusal (patch the test runner, assert zero calls).
- Assert dry-run reports the alignment verdict and writes nothing.
- Assert alignment writes only the version field and preserves the rest of the file byte-for-byte.
- Assert failure after alignment restores the original host bytes and the original repository version.

One real-host confirmation is expected at the next release: run `--real-host-validation` against the host copy left at a deliberately older version and observe a single `host_package_version_mismatch` in seconds instead of a 35-minute suite failure.
