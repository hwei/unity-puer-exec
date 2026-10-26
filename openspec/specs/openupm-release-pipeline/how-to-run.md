# Preparing an OpenUPM Release

Use the repository-local helper to prepare a source release before any remote push:

```text
python tools/release_openupm.py --version 0.2.0 --dry-run
python tools/release_openupm.py --version 0.2.0 --commit --tag
python tools/release_openupm.py --version 0.2.0 --commit --real-host-validation
python tools/release_openupm.py --version 0.2.0 --commit --real-host-validation --sync-host-version
```

## Default workflow

1. Run `--dry-run` first to confirm the planned version change, validations, and optional git actions.
2. Run the real preparation command with the requested version.
3. Review the resulting commit and local tag state.
4. Push the source commit and `v<version>` tag manually to trigger the existing GitHub Actions release pipeline.

## What the helper does

- Verifies the worktree is clean before any version edit.
- Refuses to continue if `v<version>` already exists locally or on `origin`.
- Updates `packages/com.txcombo.unity-puer-exec/package.json`.
- Runs the default mocked/unit release test suite.
- Optionally runs real-host validation when `--real-host-validation` is requested.
- Optionally creates a local release commit when `--commit` is requested.
- Optionally creates a local `v<version>` source tag when `--commit --tag` is requested.

## Host package identity prerequisite

Real-host validation is only evidence for the release when the package the host
actually loads *is* the release candidate. The host's loaded package decides its
own version, not this repository: Unity loads an embedded copy under
`Project/Packages/` ahead of the manifest's `file:` dependency whenever that
copy declares `com.txcombo.unity-puer-exec`.

With `--real-host-validation` the helper therefore runs a read-only preflight
before it writes the repository version, before either test suite, and before
the `--dry-run` return. It resolves the host exactly as the real-host suite does
(`UNITY_PROJECT_PATH`, then `.env`; there is deliberately no `--project-path`
override, so the checked host and the tested host cannot diverge) and refuses
with one of these codes:

| Code | Meaning |
|---|---|
| `host_project_unavailable` | the host path is unset, missing, or has no `Packages/manifest.json` — a refusal now, where the suite used to skip and the helper still recorded the suite as run |
| `host_package_ambiguous` | two or more immediate children of `Packages/` declare the package name; Unity loads one and the helper will not guess which |
| `host_package_not_wired` | no embedded copy and no usable `file:` dependency, so the host would load a published version instead |
| `host_package_version_mismatch` | the loaded copy declares a different version than the one being released; the message names the loaded path and both versions |
| `host_package_stale` | alignment was requested but the loaded copy's package content differs from this repository's |

A `file:` dependency that resolves to this repository's own package root is the
candidate by identity of path: real-host validation proceeds with no version
read and no host write, because the repository bump supplies the version.

## Aligning the host copy

`--sync-host-version` (valid only together with `--real-host-validation`) writes
the release candidate version into the loaded host copy's `package.json`. It is
gated on content parity over the whole package tree except `CLI~/`: relative
path sets must match, `package.json` must match as parsed JSON without its
`version` key, and other files are compared after normalising CRLF to LF (the
host is a separate git repository that rewrites line endings on checkout). Only
the `version` value is rewritten; every other byte of the file is preserved.

The write happens before the repository bump. If preparation then fails or is
interrupted before the release commit — including `Ctrl+C` during the half-hour
real-host suite — the helper restores both the host's original bytes and the
repository version. Once the release commit exists, the aligned host version
stays, so the host keeps tracking the released version.

Two remedies when the loaded copy lags:

- run again with `--sync-host-version`, if the copy's content matches this
  repository; or
- remove the embedded copy so the manifest's `file:` dependency wins. Renaming
  the directory does not clear the shadow — Unity loads it by the `name` its
  `package.json` declares.

Writing `package.json` in a host that has an Editor open makes that Editor
re-resolve packages. The real-host suite closes any running Editor for the host
and launches a fresh one regardless, so this is not a reason to close it by hand.

`--dry-run --real-host-validation` reports the same preflight verdict — loaded
path, how it was identified, both versions, and the parity verdict when
`--sync-host-version` was passed — without touching either file.

## Guardrails

- `--dry-run` is pure planning mode: no file edits, no tests, no commit, no tag.
- `--tag` requires committed release state, so use it together with `--commit`.
- `--sync-host-version` requires `--real-host-validation`; the helper refuses the combination on its own.
- The helper never pushes commits or tags.
- Remote push remains the explicit human step that triggers the CI publish flow.

## Test boundary

Default release preparation runs the same mocked/unit suite used by the repository unit-test workflow.
Real-host validation remains opt-in and environment-dependent; see [validation-host-integration/how-to-run.md](../validation-host-integration/how-to-run.md).

Opt-in changes what an absent prerequisite means. The suite itself still skips at class level when it cannot resolve the host, so `unittest` exits `0` having run nothing; the helper's preflight turns the same condition into `host_project_unavailable`, because a maintainer who passed `--real-host-validation` asked for evidence, not for a green exit code.
