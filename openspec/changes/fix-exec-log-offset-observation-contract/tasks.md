## 1. Contract

- [x] 1.1 Define the authoritative observation-log source used by both `exec --include-log-offset` and CLI log-wait commands
- [x] 1.2 Update the formal contract text for `log_offset` so callers can rely on it as an observation checkpoint

## 2. Implementation

- [x] 2.1 Fix package and/or CLI code so returned `log_offset` is measured against the same log source consumed by observation commands
- [x] 2.2 Add or update automated tests covering the corrected `log_offset` behavior

## 3. Real Host Validation

- [x] 3.1 Validate `exec --include-log-offset` plus `wait-for-result-marker` against `c3-client-tree2/Project`
- [x] 3.2 Validate `exec --include-log-offset` plus `wait-for-log-pattern --extract-json-group` against `c3-client-tree2/Project`
- [x] 3.3 Record whether the corrected path works for both `completed` and `running` style execution responses

Note: real-host validation proved non-zero top-level `log_offset` for both `completed` and `running` responses. The current `running` response still returns `result: null`, so any workflow that needs a `correlation_id` before completion still depends on how the script makes that id available.
