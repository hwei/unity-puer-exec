## 1. Prune Confirmed-Dead Runtime Surfaces

- [x] 1.1 Confirm repository-local removal candidates and delete the confirmed-dead transitional helpers
- [x] 1.2 Remove or tighten tests and assertions that still mention deleted transitional helpers
- [x] 1.3 Record any still-uncertain compatibility surfaces as explicit shim candidates instead of deleting them blindly

## 2. Isolate Compatibility Shims

- [x] 2.1 Reduce `unity-puer-session` to a clearly marked compatibility adapter with no independent business logic
- [x] 2.2 Isolate compile-trigger compatibility code from the primary Unity Editor runtime path
- [x] 2.3 Update README, help text, and code comments so compatibility surfaces are described as non-authoritative

## 3. Refactor Python Runtime Structure

- [x] 3.1 Extract shared CLI command metadata and thin the `unity_puer_exec.py` entry module
- [x] 3.2 Split session/runtime responsibilities into focused modules while preserving current behavior
- [x] 3.3 Update Python unit tests to validate the new module seams and preserved CLI contract

## 4. Refactor Unity Editor Runtime Structure

- [x] 4.1 Split server lifecycle, job state, script wrapping, and bridge code out of `UnityPuerExecServer.cs`
- [x] 4.2 Keep transitional compatibility code either deleted or confined to explicit compatibility files
- [x] 4.3 Update package-layout and runtime-focused tests for the new Editor file structure

## 5. Validate and Close Out

- [x] 5.1 Run repository test suites covering CLI contract, session runtime, and package layout
- [x] 5.2 Run any targeted host-validation evidence needed to confirm no regression in the critical real-host CLI workflow
- [x] 5.3 Review the change for archive readiness and summarize whether any follow-up compatibility cleanup remains
