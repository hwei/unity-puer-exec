## ADDED Requirements

### Requirement: Continuation candidates carry the selector-appropriate argv

When a continuation candidate names a command that accepts both `--project-path` and
`--base-url`, and the response is reachable under either selector, the candidate SHALL carry an
`argv` variant for each addressing mode and SHALL emit the variant matching the selector the
caller used. The candidate SHALL NOT omit `argv` when the selector it was reached through is
present and the command accepts that selector.

#### Scenario: A base-url wait-for-exec continuation carries a base-url argv

- **WHEN** `wait-for-exec --base-url ...` returns `running` for an accepted request
- **THEN** the `wait-for-exec` candidate's `argv` names `--base-url` and the request id
- **AND** it does not name `--project-path`

#### Scenario: A base-url completed response carries a runnable error sweep

- **WHEN** `exec --base-url ...` returns `completed` with a CLI-owned `log_range`
- **THEN** the `get-log-briefs` candidate's `argv` names `--base-url`, `--range`, and
  `--levels error,warning`
- **AND** it omits `argv` rather than being removed only when the selector value is absent

#### Scenario: A project-path continuation is unchanged

- **WHEN** the same candidate is reached through `--project-path`
- **THEN** its `argv` names `--project-path` and not `--base-url`
