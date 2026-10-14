# Design

## Context

See proposal.md - Why. `.github/workflows/release.yml` triggers on `v*` tag pushes. It validates the
tag against `packages/com.txcombo.unity-puer-exec/package.json`, builds `unity-puer-exec.exe` with
PyInstaller, assembles a UPM package tree into `$UPM_STAGE_DIR`, then force-pushes that tree to the
`upm` branch and creates the `upm/v<version>` tag. OpenUPM consumes the `upm/v*` tag.

The durable spec `openupm-release-pipeline` currently constrains the published file set and tagging,
but says nothing about a GitHub Release artifact. `gh release` is not used anywhere yet.

Key already-satisfied constraint: the `publish` job already has `permissions: contents: write`,
which `gh release create` needs.

## Goals / Non-Goals

**Goals:**

- Attach the complete installable UPM package (including the built CLI) to a GitHub Release for
  every `v*` tag.
- Keep the tarball out of the force-pushed `upm` branch content.
- Keep the step safe to re-run.

**Non-Goals:**

- Replacing or changing OpenUPM registration or the `upm` branch flow.
- Publishing to GitHub Packages (GitHub has no UPM registry).
- Attaching a bare `.exe`; the CLI is only usable inside the package.
- Changing package contents or `package.json`.

## Decisions

### Decision 1: Use `npm pack` output (`.tgz`) as the release artifact

`npm pack` is the registry-standard format OpenUPM itself serves, and Unity 2022.3 installs it
directly via Package Manager "Add package from tarball" or a `file:` manifest entry. Alternatives
considered:

- **GitHub auto source archive of the `upm/v*` tag** - rejected. It is a git archive with its own
  root folder and no npm normalization, so Unity cannot install it as a tarball.
- **Zip of the package tree** - rejected as the primary artifact. Not directly installable; only
  useful for inspection.
- **Bare `.exe`** - rejected. Useless without the hosting package.

### Decision 2: Pack into a destination outside `$UPM_STAGE_DIR`

The `Publish upm branch and tag` step copies `$UPM_STAGE_DIR/*` into the `upm` branch. Packing into
the stage tree would commit the `.tgz` into the branch. Using `npm pack --pack-destination <dir>`
with `<dir>` under `$RUNNER_TEMP` avoids this and leaves the publish step untouched.

### Decision 3: Idempotent release step

`gh release create` fails if the Release already exists, which would break a workflow re-run. The
step checks `gh release view`; when the Release exists it uploads the asset with `--clobber`,
otherwise it creates the Release with `--generate-notes` and the asset.

### Decision 4: Release notes are auto-generated

`--generate-notes` derives notes from commits/PRs since the previous tag, which is the reason to
populate Releases in the first place and requires no extra maintenance.

## Risks / Trade-offs

**[`release.yml` only runs on `v*` tag pushes, so the new steps cannot be exercised by a normal
push]** → Verify the workflow syntax locally and confirm on the next real release. If none occurs
before archive, record a `validation-gap` in closeout.

**[`npm pack` falls back to `.gitignore` when no `.npmignore` is present]** → The assembled stage
tree contains neither file, so all required assets (including `CLI~/unity-puer-exec.exe`) are
packed. Task 4.1 verifies this.

**[Package contents differ from the `upm` branch / OpenUPM build if assembly changes later]** → The
tarball is produced from the same `$UPM_STAGE_DIR` as the `upm` branch push, so the two artifacts
cannot drift within a run.
