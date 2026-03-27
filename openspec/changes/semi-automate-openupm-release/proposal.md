## Why

The repository already automates OpenUPM publishing after a maintainer pushes a matching `v*` tag, but the local preparation steps are still manual: update `package.json`, verify the tree is safe to release from, run the default test suite, commit, and tag. That handoff is small but error-prone, and the earlier `publish-to-openupm` change explicitly left automated version bumping out of scope.

## What Changes

- Add a local Python release helper for maintainers, tentatively `python tools/release_openupm.py --version <x.y.z>`.
- Let the helper update `packages/com.txcombo.unity-puer-exec/package.json`, run release preflight checks, and execute the default mocked/unit test suite before a version tag is pushed.
- Support optional local release commit creation and optional local `v<version>` tag creation, while keeping remote `git push` as a human-controlled step.
- Support a no-side-effect `--dry-run` mode that reports the intended version bump, checks, tests, and git actions without modifying repository state.
- Keep the existing GitHub Actions and OpenUPM branch/tag pipeline as the canonical publish path after the local preparation step completes.

## Capabilities

### New Capabilities
- `openupm-release-helper`: Local maintainer workflow for preflighting an OpenUPM release, bumping the package version, optionally creating a release commit and local source tag, and supporting dry-run planning.

### Modified Capabilities
- `openupm-release-pipeline`: Document how the local helper prepares a release without replacing the existing `v*` tag driven CI publish contract.

## Impact

- **New tool**: a repository-local Python release helper under `tools/`.
- **Git workflow**: local release preparation becomes standardized and safer, but remote push and actual publishing remain explicit human actions.
- **Tests**: the helper will invoke the same default mocked/unit suite already used by CI, with optional real-host coverage left opt-in.
- **OpenSpec**: durable release workflow requirements will expand to cover the local preflight helper in addition to the existing CI publish pipeline.
