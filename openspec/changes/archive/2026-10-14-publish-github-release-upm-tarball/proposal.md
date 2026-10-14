## Why

The GitHub repository publishes OpenUPM and `upm`-branch artifacts on every `v*` tag, but the
GitHub **Releases** section is empty: `.github/workflows/release.yml` creates git tags only and
never creates a Release object. The repository therefore shows version tags with no downloadable,
human-facing release artifact, even though the CI already assembles a complete UPM package tree
(including the built `unity-puer-exec.exe` under `CLI~`).

A bare `.exe` is not a usable release artifact because the CLI cannot run without the Unity package
that hosts the Puerts bridge. The correct release artifact is the **complete UPM package** in the
registry-standard `.tgz` (npm pack) format, which Unity 2022.3 can install directly.

## What Changes

- In `.github/workflows/release.yml`, after the UPM package tree is assembled, run `npm pack` to
  produce `com.txcombo.unity-puer-exec-<version>.tgz` from that tree, staged outside the tree so it
  is not force-pushed onto the `upm` branch.
- Add a `Create GitHub Release` step that creates a Release for the pushed `v<version>` tag, with
  auto-generated notes and the `.tgz` attached as the release asset.
- Make the release step idempotent so a workflow re-run does not fail when the Release already
  exists (upload with `--clobber` instead of creating again).
- Keep the existing OpenUPM / `upm` branch publishing path unchanged.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `openupm-release-pipeline`: add requirements that the release workflow produces an installable
  UPM `.tgz` and attaches it to a GitHub Release, and that the tarball contains the full package
  (including the built CLI under `CLI~`).

## Impact

- Affected files: `.github/workflows/release.yml`,
  `openspec/specs/openupm-release-pipeline/spec.md` (via delta).
- Affected behavior: each `v*` tag push additionally creates a GitHub Release with the UPM tarball.
- Affected validation: confirmed by a real `v*` tag run (CI transcript) plus a local `npm pack`
  check on the assembled tree; `release.yml` is only exercisable on a tag push.
