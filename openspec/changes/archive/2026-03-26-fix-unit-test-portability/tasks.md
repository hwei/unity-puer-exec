## 1. Validation-host dependency portability

- [x] 1.1 Update validation-host dependency computation to preserve same-anchor relative paths and handle cross-volume Windows paths deterministically.
- [x] 1.2 Extend validation-host helper tests to cover both reproducible relative paths and cross-volume fallback behavior.

## 2. Unit-test hermeticity

- [x] 2.1 Replace the Unity version unit test's real `UNITY_PROJECT_PATH` dependency with a repository-local temporary fixture.
- [x] 2.2 Re-run the GitHub Actions unit-test command locally to confirm the previously failing cases pass.
