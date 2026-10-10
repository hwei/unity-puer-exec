# Proposal

## Why

The server-side behavior added by `disclose-play-mode-block-in-wait-for-exec` — retaining
the exec refresh block on the job when play mode suppressed the refresh, and replaying it on
a `wait-for-exec` terminal response — is covered only by the opt-in real-host suite. That
suite needs a live Editor and a prepared validation host, and one play-mode case costs
several minutes. A regression in the replay payload (`BuildExecResponseJson`) or in the job
retention would therefore either escape detection or require a full host run to notice.

The Unity package has no EditMode test assembly at all, so pure server-side response
construction is not unit-covered. The response builders and the job snapshot are plain C#
and do not need the CLI, the control endpoint, or a running Editor to exercise.

## What Changes

- Add an EditMode test assembly to the package under `Tests/EditMode/`, constrained to the
  Editor test platform, referencing the Editor assembly and the Unity test framework.
- Add tests for the pure server-side response path: the refresh block is retained only for a
  play-mode suppression, is replayed by `BuildExecResponseJson` for a terminal snapshot, is
  not replayed for other refresh outcomes, and does not leak between jobs.
- Add a repository-local way to run the EditMode tests headlessly (Unity batch mode with
  `-runTests -testPlatform EditMode`), so a maintainer can run them without the real-host CLI
  flow. This stays outside the default Python unit-test workflow.
- Leave the real-host play-mode case in place as the end-to-end backstop; the EditMode tests
  do not replace it.
- Keep the `Tests/` tree out of the published UPM package. The release assembly already
  copies an explicit allowlist, so no release-workflow change is expected.

## Capabilities

### New Capabilities

- `package-editmode-test-harness`: a fast, in-Editor unit-test surface for pure Unity-package
  server behavior, separate from the real-host regression suite.

### Modified Capabilities

(none)

## Impact

- `packages/com.txcombo.unity-puer-exec/Tests/EditMode/`: new test assembly, test sources,
  asmdef, and committed `.meta` files.
- A repository-local runner (tool script and/or the validation how-to-run document) that
  launches Unity batch mode for EditMode tests.
- `tests/`: a Python guard for the harness's presence and shape may be added to the default
  suite; the `.meta`/layout guard may need to account for the new tree.
- No product API, wire protocol, or CLI behavior change. No new field, command, or flag.
- Follow-up origin: `disclose-play-mode-block-in-wait-for-exec` (validation-gap).
