## 1. Package Metadata

- [ ] 1.1 Update `packages/com.txcombo.unity-puer-exec/package.json`: add `license: "MIT"`, `repository` field pointing to GitHub repo, update `author.name` to `Will Huang`, add `dependencies` with `com.tencent.puerts.core: "3.0.0"`
- [ ] 1.2 Add `LICENSE` file (MIT) to `packages/com.txcombo.unity-puer-exec/`

## 2. GitHub Actions Workflow

- [ ] 2.1 Create `.github/workflows/release.yml` with trigger on `v*` tag push
- [ ] 2.2 Implement version consistency check: extract version from package.json, verify it matches the pushed tag, fail with clear error on mismatch
- [ ] 2.3 Implement PyInstaller build step: setup Python 3.12, install PyInstaller, build `unity-puer-exec.exe` with `--onefile --paths=cli/python --name unity-puer-exec`
- [ ] 2.4 Implement UPM package assembly step: copy Editor/, package.json, LICENSE into staging dir; place exe into staging CLI~/ directory
- [ ] 2.5 Implement upm branch publish step: force-push staging tree to `upm` branch, create `upm/v<version>` tag

## 3. Validation

- [ ] 3.1 Add a package-layout test that verifies the expected files exist in `packages/com.txcombo.unity-puer-exec/` (package.json fields, LICENSE)
- [ ] 3.2 Manually test the workflow by pushing a `v0.0.1` tag to the GitHub repo and verifying the `upm` branch and `upm/v0.0.1` tag are created correctly

## 4. OpenUPM Registration

- [ ] 4.1 Prepare OpenUPM package listing YAML (`com.txcombo.unity-puer-exec.yml`) with `gitTagPrefix: upm/`, license, topics
- [ ] 4.2 Submit PR to `openupm/openupm` repository to register the package
