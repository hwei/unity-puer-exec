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

### D6. The host wiring step declares the package testable

Unity compiles and discovers a package's own test assemblies only when the package is listed in
the consuming project's `manifest.json` `testables` list. That was discovered by running the new
harness against the wired host: without the entry,
`Unity -batchMode -runTests -testPlatform EditMode` exits `0` having run nothing, so the harness
reads as a pass while covering nothing. The declaration therefore belongs to the same
repository-owned step that already injects the local package dependency
(`tools/prepare_validation_host.py`), which is what `how-to-run.md` calls a prepared host. The
rewrite is additive and idempotent and preserves unrelated `testables` entries, so a host wired
for the runtime package stays wired for the package's tests.

The runner still guards the failure mode: a launch that discovers no test of the package
assembly is reported as `no_tests_discovered`, not as a pass, so a host wired by hand or by an
older tool version cannot silently pass.

### D7. The Editor assembly grants internals to the test assembly

The covered types (`UnityPuerExecJob`, `UnityPuerExecJobSnapshot`, `UnityPuerExecProtocol`) are
`internal`. The test assembly reaches them through an `InternalsVisibleTo` grant in
`Editor/AssemblyInfo.cs` rather than by making them public, because the proposal pins the public
API as unchanged and the tests exist to protect current behavior, not to expand the surface.

## Risks

- A test assembly that accidentally compiles into player builds or the published package. The
  Editor-only platform, the include constraint, and the release allowlist each guard this;
  the layout guard tests the first two.
- EditMode tests that quietly depend on Editor state and become flaky. The first coverage is
  deliberately pure function and job-state assertions, which do not touch Editor state.
- A host whose manifest lacks the `testables` declaration compiles no test assembly at all and
  makes a batch test launch exit `0`. The wiring step declares it, and the runner reports the
  resulting empty discovery as a failure, so the condition cannot read as a pass.
