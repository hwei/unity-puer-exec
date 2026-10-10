## 1. EditMode test assembly

- [x] 1.1 Add `packages/com.txcombo.unity-puer-exec/Tests/EditMode/UnityPuerExec.EditMode.Tests.asmdef`, restricted to the Editor platform, referencing `UnityPuerExec.Editor` and the Unity test framework, and gated by the test framework include constraint. Commit the folder and asmdef `.meta` files. Verify: the Unity project imports the folder and compiles with no errors.
- [x] 1.2 Add EditMode tests covering the refresh-block retention and replay: a play-mode suppression is retained on the job and replayed by the terminal response builder; a triggered (non-suppressed) refresh is not retained or replayed; retention does not leak between jobs. Verify: green in the Unity Test Runner.

## 2. Headless runner and documentation

- [x] 2.1 Add a repository-local command that runs the EditMode tests in Unity batch mode (`-runTests -testPlatform EditMode` with a results file), reusing the batch-mode launch approach the compile preflight already uses. Verify: the documented command produces a test-results file.
- [x] 2.2 Document the harness in `openspec/specs/validation-host-integration/how-to-run.md`, stating that it is distinct from the real-host suite and remains outside the default Python unit-test workflow.
- [x] 2.3 Declare the package in the validation host manifest's `testables` list from `tools/prepare_validation_host.py`, idempotently and without disturbing unrelated entries, with Python coverage for the declaration. Verify: the default suite is green and a re-prepared host reports the package as testable.

## 3. Guards and validation

- [x] 3.1 Add a guard to the default Python suite asserting the EditMode assembly exists, is Editor-only, references the package Editor assembly and the test framework, and carries the include constraint. Verify: the guard fails when the asmdef is missing or mis-scoped.
- [x] 3.2 Run the default Python suite. Verify: green.
- [x] 3.3 Run the EditMode tests headlessly against a prepared project. Verify: green.
- [x] 3.4 Run `openspec validate add-package-editmode-tests`. Verify: green.
