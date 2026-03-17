## 1. Contract

- [ ] 1.1 Define the authoritative observation-log source used by both `exec --include-log-offset` and CLI log-wait commands
- [ ] 1.2 Update the formal contract text for `log_offset` so callers can rely on it as an observation checkpoint

## 2. Implementation

- [ ] 2.1 Fix package and/or CLI code so returned `log_offset` is measured against the same log source consumed by observation commands
- [ ] 2.2 Add or update automated tests covering the corrected `log_offset` behavior

## 3. Real Host Validation

- [ ] 3.1 Validate `exec --include-log-offset` plus `wait-for-result-marker` against `c3-client-tree2/Project`
- [ ] 3.2 Validate `exec --include-log-offset` plus `wait-for-log-pattern --extract-json-group` against `c3-client-tree2/Project`
- [ ] 3.3 Record whether the corrected path works for both `completed` and `running` style execution responses
