# Tasks

## 1. Pack the UPM package as a tarball

- [x] 1.1 In `.github/workflows/release.yml`, add a `Pack UPM tarball` step after `Assemble UPM package tree`. It runs `npm pack --pack-destination <dir>` from `$UPM_STAGE_DIR` into a directory outside the stage tree. Verify: the step fails loudly if `com.txcombo.unity-puer-exec-<version>.tgz` is not produced, and it exports the tarball path via `$GITHUB_ENV`.
- [x] 1.2 Confirm the tarball is not copied into the published tree. Verify: `Publish upm branch and tag` still copies only `$UPM_STAGE_DIR/*` and the pack destination is outside that directory.

## 2. Create the GitHub Release

- [x] 2.1 Add a `Create GitHub Release` step at the end of the `publish` job using `gh release create "${{ steps.version.outputs.tag }}"` with `--generate-notes` and the tarball as the asset. Verify: `GH_TOKEN` is set from `github.token` and the job retains `permissions: contents: write`.
- [x] 2.2 Make the step idempotent for workflow re-runs. Verify: if a Release for the tag already exists, the step uploads the tarball with `--clobber` rather than failing on create.

## 3. Update the durable spec

- [x] 3.1 Write the delta spec for `openupm-release-pipeline` adding the UPM-tarball and GitHub-Release requirements with scenarios. Verify: `openspec validate publish-github-release-upm-tarball --strict` passes.

## 4. Validation and Closeout

- [x] 4.1 Locally verify the pack command shape against the package tree. Verify: `npm pack` semantics hold (no `.npmignore`/`.gitignore` in the package root excludes required assets) or record the result under `.tmp/`.
- [x] 4.2 Confirm the assembled tree used by CI contains exactly `Editor/`, `Editor.meta`, `CLI~/`, `package.json`, `package.json.meta`, `LICENSE`, `LICENSE.meta`, `README.md`, `README.md.meta`. Verify: read the `Assemble UPM package tree` step.
- [ ] 4.3 After the change lands, confirm on the next real `v*` tag run that a GitHub Release exists with the `.tgz` asset. If no release has occurred before archive, record the unverified release run as a `validation-gap`.
- [ ] 4.4 Complete the required apply closeout review and record the finding with allowed categories.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
