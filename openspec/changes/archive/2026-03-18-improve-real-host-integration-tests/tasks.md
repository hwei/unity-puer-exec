## 1. Real-Host Regression Entry Point

- [x] 1.1 Add a repository-owned real-host integration test entry point under `tests/` that runs only when a usable validation host path is available
- [x] 1.2 Reuse repository-owned host preparation so the real-host regression path can deterministically wire the external Unity project before runtime checks

## 2. Critical CLI Flow Coverage

- [x] 2.1 Add real-host coverage for the project-scoped readiness flow and fail clearly when Unity never becomes ready
- [x] 2.2 Add real-host coverage for `exec --include-log-offset` followed by `wait-for-result-marker` from the returned checkpoint
- [x] 2.3 Add real-host coverage for `wait-for-log-pattern --extract-json-group` against the same emitted marker and compatible observation checkpoint

## 3. Validation Workflow Closeout

- [x] 3.1 Document how contributors run the mocked suite versus the opt-in real-host regression path and how to interpret failures
- [x] 3.2 Run the new real-host regression workflow against the validation host and capture the evidence needed to close the change
