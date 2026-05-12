## 1. Rename root readme files and update cross-references

- [ ] 1.1 Rename root `ReadMe.md` → `README.md` (git mv)
- [ ] 1.2 Rename root `ReadMe.zh-CN.md` → `README.zh-CN.md` (git mv)
- [ ] 1.3 Update `README.zh-CN.md` language switcher links: `ReadMe.md` → `README.md`, `ReadMe.zh-CN.md` → `README.zh-CN.md`
- [ ] 1.4 Update `openspec/specs/readme-agent-onboarding/spec.md`: all `ReadMe.md` → `README.md`, all `ReadMe.zh-CN.md` → `README.zh-CN.md`
- [ ] 1.5 Update `openupm/com.txcombo.unity-puer-exec.yml`: `readme: "main:ReadMe.md"` → `readme: "main:README.md"`

## 2. Add README.md to UPM package directory

- [ ] 2.1 Copy root `README.md` into `packages/com.txcombo.unity-puer-exec/README.md` (this is a committed file, not CI-only)
- [ ] 2.2 Add `"readme": "README.md"` field to `packages/com.txcombo.unity-puer-exec/package.json`
- [ ] 2.3 If Unity generates `README.md.meta`, commit it alongside the package README

## 3. Update CI release workflow

- [ ] 3.1 Add `Copy-Item "packages/com.txcombo.unity-puer-exec/README.md" -Destination $stageDir` line to `.github/workflows/release.yml`
- [ ] 3.2 If `README.md.meta` exists in the package dir, add its `Copy-Item` line too

## 4. Update tests

- [ ] 4.1 Add test `test_published_package_includes_readme` to `tests/test_package_layout.py` asserting `README.md` exists in the package directory
- [ ] 4.2 If README.md.meta is added, update `test_release_workflow_copies_required_root_meta_files` to assert the meta copy line

## 5. Verify

- [ ] 5.1 Run `python -m pytest tests/ -v` to confirm all tests pass
- [ ] 5.2 Verify both language switchers work (English ↔ Chinese links correct after rename)
- [ ] 5.3 Confirm `README.md` and `README.zh-CN.md` render correctly on GitHub (renamed, links intact)
