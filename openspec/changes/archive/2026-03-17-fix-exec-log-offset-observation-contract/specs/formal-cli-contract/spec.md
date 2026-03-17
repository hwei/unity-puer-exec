## MODIFIED Requirements

### Requirement: Long-running execution remains machine-usable through log-driven observation

Long-running execution SHALL remain machine-usable without token-driven continuation. `exec` SHALL provide enough machine-readable information for a caller to observe the intended long-running work, including an explicit opt-in path for returning the observation start offset used by result-marker waiting. When that opt-in path is requested, `exec` SHALL return top-level `log_offset` consistently for both `completed` and `running` responses. That `log_offset` SHALL be measured against the same log source consumed by `wait-for-log-pattern` and `wait-for-result-marker`, so callers can rely on it as an observation checkpoint. `wait-for-log-pattern` SHALL remain the regex-oriented observation primitive and SHALL support extraction modes including parsed JSON group extraction for structured markers. The extraction modes that return plain text and parsed JSON SHALL be mutually exclusive. The CLI SHALL provide a higher-level `wait-for-result-marker` path for the recommended single-line JSON result-marker workflow so callers do not need to author brittle full-JSON regexes themselves.

#### Scenario: Caller starts observation from the returned checkpoint

- **WHEN** a caller invokes `exec --include-log-offset` and then starts either `wait-for-result-marker` or `wait-for-log-pattern` from the returned `log_offset`
- **THEN** the returned offset is compatible with the observer's actual log source
- **AND** the caller does not need to fall back to scanning from the beginning of the log to find the intended marker
