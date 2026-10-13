## REMOVED Requirements

### Requirement: Success-path observation windows carry an error-sweep follow-up

## ADDED Requirements

### Requirement: Success-path observation windows carry a selector-appropriate error sweep

When `exec`, `wait-for-exec`, or `wait-for-log-pattern` returns `status = "completed"` with a
CLI-owned `log_range`, the response SHALL include a `get-log-briefs` candidate whose `argv` is a
complete invocation using `--range <start>-<end>` built from the observed span and
`--levels error,warning`, addressed to the selector the caller used.

#### Scenario: exec completed offers a copyable error sweep

- **WHEN** `exec` returns `status = "completed"` with `log_range.start` and `log_range.end` present and a project-path selector available
- **THEN** the response includes a `next_steps` entry with `command = "get-log-briefs"`
- **AND** that entry's `argv` includes `--range` with the value `{log_range.start}-{log_range.end}`
- **AND** that entry's `argv` includes `--levels` with the value `error,warning`

#### Scenario: wait-for-exec completed offers the same error sweep

- **WHEN** `wait-for-exec` returns `status = "completed"` with `log_range.start` and `log_range.end` present and a project-path selector available
- **THEN** the response includes a `next_steps` entry with `command = "get-log-briefs"`
- **AND** that entry's `argv` includes the same `--range` and `--levels error,warning` shape as the `exec` completed case

#### Scenario: wait-for-log-pattern completed offers the error sweep and explains the limit of a match

- **WHEN** `wait-for-log-pattern` returns `status = "completed"` with `log_range.start` and `log_range.end` present and a project-path selector available
- **THEN** the response includes a `situation` string stating that a pattern match does not imply the observation window contained no new errors or warnings
- **AND** the response includes a `next_steps` entry with `command = "get-log-briefs"` whose `argv` re-scans that window with `--levels error,warning`

#### Scenario: A base-url completed response carries a base-url error sweep

- **WHEN** `exec` returns `status = "completed"` with `log_range.start` and `log_range.end` present and a `--base-url` selector
- **THEN** the response includes a `next_steps` entry with `command = "get-log-briefs"`
- **AND** that entry's `argv` names `--base-url`, `--range` with the observed span, and `--levels error,warning`
- **AND** that entry's `argv` does not name `--project-path`

#### Scenario: Script result does not change the success-path candidates

- **WHEN** `exec` returns `status = "completed"` with two different script-authored `result` values across otherwise identical envelopes
- **THEN** both responses carry the same `next_steps` candidate set for that command and status
