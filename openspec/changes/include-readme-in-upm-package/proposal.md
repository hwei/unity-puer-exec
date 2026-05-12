## Why

The UPM package currently ships without a README. The README is the primary onboarding surface for AI agents — it contains the agent prompts that tell agents how to discover and use the `unity-puer-exec` CLI. Without it in the installed package, agents (and human users browsing the local package directory) have no local reference. Separately, the file is named `ReadMe.md` (mixed case) while the UPM ecosystem convention is `README.md` (all caps). This change brings the README into the publishable package tree and normalizes the filename.

## What Changes

- Rename root `ReadMe.md` → `README.md` and `ReadMe.zh-CN.md` → `README.zh-CN.md` (normalize to all-caps convention)
- Add `README.md` to the CI release workflow's `Copy-Item` list so it ships in the UPM package
- Add `"readme": "README.md"` field to `packages/com.txcombo.unity-puer-exec/package.json` for Unity Package Manager UI rendering
- Update OpenUPM registration config to reference `main:README.md`
- Update the openupm-release-pipeline spec to include README.md as a publishable asset and require the `"readme"` field
- Add a package-layout test asserting README.md is present in the UPM package dir
- Chinese README (`README.zh-CN.md`) stays at root but is NOT included in the UPM package

## Capabilities

### New Capabilities

<!-- None — this change modifies an existing pipeline requirement rather than introducing a new capability. -->

### Modified Capabilities

- `openupm-release-pipeline`: add `README.md` to the set of publishable package assets; add requirement that `package.json` includes a `"readme"` field pointing to `README.md`
- `readme-agent-onboarding`: update all `ReadMe.md` / `ReadMe.zh-CN.md` references to `README.md` / `README.zh-CN.md` (filenames only, requirements unchanged)

## Impact

- `ReadMe.md` → `README.md`, `ReadMe.zh-CN.md` → `README.zh-CN.md`: any external links or references to old names in the repo need updating
- CI workflow adds one `Copy-Item` line
- `package.json` gains one field (no breaking change for existing consumers)
- OpenUPM web display continues to work via updated `readme: "main:README.md"` path
