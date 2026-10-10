# Design

## Context

`disclose-play-mode-block-in-wait-for-exec` established that the server retains the exec-time
refresh block on the job when play mode suppressed the refresh, and replays it on a
`wait-for-exec` terminal response. Its real-host run exposed the original design gap: the
completed-request replay previously carried no refresh block. That finding remains true and
the retention is now in place.

The gap this change addresses is validation, not behavior. The retention and replay live in
`UnityPuerExecJob` / `UnityPuerExecJobSnapshot` and `UnityPuerExecProtocol.BuildExecResponseJson`.
Both are plain C# with no CLI, control-endpoint, or running-Editor dependency, yet the only
test that exercises them is the opt-in real-host play-mode case. That case requires a live
Editor and a prepared host, and one invocation costs several minutes, so a fast regression
signal does not exist.

## Decisions

### D1. The EditMode assembly lives in the package, not in the validation host

The validation host is explicitly not the product source of truth. A test assembly placed
only there would not travel with the package and would not be part of the reviewed source.
The assembly lives under `packages/com.txcombo.unity-puer-exec/Tests/EditMode/` and runs
against the host only because the host wires the local package. This keeps the tests beside
the code they cover.

### D2. First coverage is the response path just added, not the whole server

The new assembly covers the refresh-block retention and the terminal response rendering:
retained only for a play-mode suppression, replayed for a terminal snapshot, absent
otherwise, and not shared between jobs. These are the exact behaviors whose only current
coverage is the slow real-host case. Broader server behavior stays with the real-host suite,
which remains the end-to-end backstop; the EditMode assembly does not try to reproduce the
control endpoint, HTTP, or file-watcher integration.

### D3. The assembly definition is Editor-test-only

The asmdef sets `includePlatforms: ["Editor"]`, references `UnityPuerExec.Editor`, and
references the Unity test framework assemblies. It carries the test framework's include
constraint so the assembly compiles only when tests are included and never enters a player
build. Committed `.meta` files keep the folder and asmdef stable for Unity's importer.

### D4. The Tests tree is not published

The release workflow assembles the UPM package from an explicit allowlist (`Editor` plus root
files). `Tests/` is intentionally outside that allowlist, so this harness stays a
source-repository development surface and no release-workflow change is needed. If the tests
were ever wanted by package consumers, that would be a separate release decision.

### D5. The harness is a documented batch-mode command, not part of the default suite

The repository already launches a batch-mode Editor for the preflight compile check, so the
same mechanism runs the EditMode tests (`-runTests -testPlatform EditMode` with a results
file). The command is documented alongside the validation-host instructions. It stays out of
the default Python unit-test workflow, which runs on a machine with no Unity Editor, so that
workflow neither invokes nor depends on the harness. A small Python guard can assert the
assembly exists and is well-formed without needing Unity.

## Risks

- A test assembly that accidentally compiles into player builds or the published package. The
  Editor-only platform, the include constraint, and the release allowlist each guard this;
  the layout guard tests the first two.
- EditMode tests that quietly depend on Editor state and become flaky. The first coverage is
  deliberately pure function and job-state assertions, which do not touch Editor state.
