## 1. Rename root readme files and update cross-references

- [x] 1.1 Rename root `ReadMe.md` → `README.md` (git mv)
- [x] 1.2 Rename root `ReadMe.zh-CN.md` → `README.zh-CN.md` (git mv)
- [x] 1.3 Update `README.zh-CN.md` language switcher links: `ReadMe.md` → `README.md`, `ReadMe.zh-CN.md` → `README.zh-CN.md`
- [x] 1.4 Update `openspec/specs/readme-agent-onboarding/spec.md`: all `ReadMe.md` → `README.md`, all `ReadMe.zh-CN.md` → `README.zh-CN.md`
- [x] 1.5 Update `openupm/com.txcombo.unity-puer-exec.yml`: `readme: "main:ReadMe.md"` → `readme: "main:README.md"`

## 2. Add README.md to UPM package directory

- [x] 2.1 Copy root `README.md` into `packages/com.txcombo.unity-puer-exec/README.md` (this is a committed file, not CI-only)
- [x] 2.2 Add `"readme": "README.md"` field to `packages/com.txcombo.unity-puer-exec/package.json`
- [x] 2.3 Unity hasn't generated `README.md.meta` automatically, so we manually created it with a unique GUID (matching the `DefaultImporter` pattern used by `LICENSE.meta`)

## 3. Update CI release workflow

- [x] 3.1 Add `Copy-Item "packages/com.txcombo.unity-puer-exec/README.md" -Destination $stageDir` line to `.github/workflows/release.yml`
- [x] 3.2 Add `Copy-Item "packages/com.txcombo.unity-puer-exec/README.md.meta" -Destination $stageDir` line alongside the README copy

## 4. Update tests

- [x] 4.1 Add test `test_published_package_includes_readme` to `tests/test_package_layout.py` asserting `README.md` exists in the package directory
- [x] 4.2 Added `"README.md"` to `UNITY_IMPORTED_PUBLISHABLE_ASSETS` tuple and added `README.md.meta` assertion in `test_release_workflow_copies_required_root_meta_files`

## 5. Verify

- [x] 5.1 Run `python -m pytest tests/ -v` to confirm all tests pass
- [x] 5.2 Verify both language switchers work (English ↔ Chinese links correct after rename)
- [x] 5.3 Confirm `README.md` and `README.zh-CN.md` render correctly on GitHub (renamed, links intact)
