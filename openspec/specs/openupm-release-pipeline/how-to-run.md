# Preparing an OpenUPM Release

Use the repository-local helper to prepare a source release before any remote push:

```text
python tools/release_openupm.py --version 0.2.0 --dry-run
python tools/release_openupm.py --version 0.2.0 --commit --tag
python tools/release_openupm.py --version 0.2.0 --commit --real-host-validation
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

## Guardrails

- `--dry-run` is pure planning mode: no file edits, no tests, no commit, no tag.
- `--tag` requires committed release state, so use it together with `--commit`.
- The helper never pushes commits or tags.
- Remote push remains the explicit human step that triggers the CI publish flow.

## Test boundary

Default release preparation runs the same mocked/unit suite used by the repository unit-test workflow.
Real-host validation remains opt-in and environment-dependent; see [validation-host-integration/how-to-run.md](../validation-host-integration/how-to-run.md).
