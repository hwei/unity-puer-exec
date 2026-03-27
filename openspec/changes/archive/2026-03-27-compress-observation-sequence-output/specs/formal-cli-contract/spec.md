## MODIFIED Requirements

### Requirement: Async execution remains machine-usable without continuation tokens

Long-running execution SHALL remain machine-usable without token-driven continuation. `exec` SHALL return `log_range` and `brief_sequence` in every response so callers can observe the operation window without an opt-in flag. `log_range.start` SHALL be the authoritative observation checkpoint for `wait-for-log-pattern` and `wait-for-result-marker`, replacing the former `log_offset` field. Any response that includes `brief_sequence` SHALL use the compact run encoding defined by `log-brief` rather than a fully expanded repeated-character string.

#### Scenario: Caller observes a long import-heavy request

- **WHEN** `exec`, `wait-for-exec`, or another observation-carrying response spans a long run of repeated brief kinds
- **THEN** `brief_sequence` stays compact enough for machine parsing and human scanning
- **AND** the compact form remains a faithful representation of the underlying observed brief order
