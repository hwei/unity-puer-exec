## ADDED Requirements

### Requirement: Continuation candidates carry the selector-appropriate argv

When a continuation candidate names a command that accepts both `--project-path` and
`--base-url`, and the response that carries the candidate is reachable under either selector,
the candidate SHALL carry an `argv` variant for each addressing mode and SHALL emit the variant
matching the selector the caller used. The candidate SHALL NOT omit `argv` when the selector it
was reached through is present and the named command accepts that selector.

#### Scenario: A base-url wait-for-exec continuation carries a base-url argv

- **WHEN** `wait-for-exec --base-url ...` returns `running` for an accepted request
- **THEN** the `wait-for-exec` candidate's `argv` names `--base-url` and the request id
- **AND** it does not name `--project-path`

#### Scenario: A project-path continuation is unchanged

- **WHEN** a converted candidate is reached through `--project-path`
- **THEN** its `argv` names `--project-path` and not `--base-url`

#### Scenario: A project-path-only target keeps its candidate and omits argv

- **WHEN** `exec --base-url ...` returns `completed` with a CLI-owned `log_range`
- **THEN** the `get-log-briefs` candidate is still present with `command` and `when`
- **AND** the candidate omits `argv` rather than naming a selector `get-log-briefs` does not accept

## MODIFIED Requirements

### Requirement: Success-path observation windows carry an error-sweep follow-up

When `exec`, `wait-for-exec`, or `wait-for-log-pattern` returns `status = "completed"` and the
response carries a CLI-owned `log_range` with both `start` and `end`, the response SHALL include
`next_steps` with a `get-log-briefs` candidate that re-scans that window. When the caller's
selector is one `get-log-briefs` accepts (`--project-path`), the candidate's `argv` SHALL be a
complete invocation using `--range <start>-<end>` built from `log_range.start` and
`log_range.end`, and SHALL include `--levels error,warning`. When the caller used `--base-url`,
`get-log-briefs` has no base-url form, so the candidate SHALL remain present and SHALL omit
`argv` rather than carrying a selector flag the command rejects.

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

#### Scenario: A base-url completed response keeps the error sweep without argv

- **WHEN** `exec` returns `status = "completed"` with `log_range.start` and `log_range.end` present and a `--base-url` selector
- **THEN** the response includes a `next_steps` entry with `command = "get-log-briefs"`
- **AND** that entry omits `argv`
- **AND** that entry does not name `--base-url`

#### Scenario: Script result does not change the success-path candidates

- **WHEN** `exec` returns `status = "completed"` with two different script-authored `result` values across otherwise identical envelopes
- **THEN** both responses carry the same `next_steps` candidate set for that command and status
