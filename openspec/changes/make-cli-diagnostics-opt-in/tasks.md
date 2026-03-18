## 1. Policy

- [x] 1.1 Define the default-versus-opt-in diagnostics policy for formal CLI commands
- [x] 1.2 Standardize diagnostics on a single top-level `diagnostics` field
- [x] 1.3 Include `exec` in the same diagnostics policy as the observation commands

## 2. Implementation

- [x] 2.1 Update affected commands to hide diagnostics by default
- [x] 2.2 Add a unified `--include-diagnostics` opt-in path across formal commands
- [x] 2.3 Remove `session.diagnostics` and `result.diagnostics` from the payload contract
- [x] 2.4 Update help and tests
