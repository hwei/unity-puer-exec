## ADDED Requirements

### Requirement: Success-path observation windows carry an error-sweep follow-up

When `exec`, `wait-for-exec`, or `wait-for-log-pattern` returns `status = "completed"` and the response carries a CLI-owned `log_range` with both `start` and `end`, the response SHALL include `next_steps` with a `get-log-briefs` candidate whose `argv` is a complete invocation that re-scans that window for errors and warnings. The candidate SHALL use `--range <start>-<end>` built from `log_range.start` and `log_range.end`, and SHALL include `--levels error,warning`. Candidate presence is determined by command and status alone; missing `log_range` or selector context SHALL cause the entry to omit `argv` while still carrying `command` and `when`, rather than removing the candidate or substituting a different command.

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

#### Scenario: Incomplete log_range drops argv but keeps the candidate

- **WHEN** one of the covered commands returns `status = "completed"` without both `log_range.start` and `log_range.end`
- **THEN** the `get-log-briefs` candidate is still present with `command` and `when`
- **AND** that candidate omits `argv`

#### Scenario: Script result does not change the success-path candidates

- **WHEN** `exec` returns `status = "completed"` with two different script-authored `result` values across otherwise identical envelopes
- **THEN** both responses carry the same `next_steps` candidate set for that command and status

## MODIFIED Requirements

### Requirement: Guidance covers all commands and statuses via a static matrix

The CLI SHALL maintain a static guidance matrix keyed by `(command, status)` that determines which `next_steps` and `situation` content to include in each response. The matrix SHALL cover every command in the authoritative flat command tree defined by the formal CLI contract, and all documented response statuses for each. The coverage requirement SHALL be expressed against that command tree rather than against a fixed command count, so adding a command extends the obligation automatically instead of leaving a stale number behind.

Candidate *selection* (which commands appear, in which order, and whether a `situation` is attached) SHALL be determined by the command name and status alone. The CLI SHALL NOT inspect script-authored `result` fields to filter, reorder, or replace candidates. When a selected candidate includes an `argv_template`, the CLI MAY fill placeholder values from CLI-owned response envelope fields (including `log_range`) and from invocation arguments; it SHALL NOT fill placeholders from script-authored `result`.

#### Scenario: Every documented non-success status has a guidance matrix entry

- **WHEN** a command returns any documented non-success status from the formal CLI contract
- **THEN** the guidance matrix provides either `next_steps`, `situation`, or both for that command × status combination

#### Scenario: Coverage follows the command tree

- **WHEN** a command is present in the authoritative flat command tree
- **THEN** the guidance matrix contains entries for that command
- **AND** a command added to the tree without matrix entries is detected rather than silently returning responses with no guidance

#### Scenario: Candidate selection ignores script-authored result fields

- **WHEN** the CLI constructs `next_steps` for a response
- **THEN** the candidates are determined by the command name and status alone
- **AND** the CLI does not inspect script-authored `result` fields to filter or reorder candidates

#### Scenario: Argv values may use CLI-owned envelope fields

- **WHEN** a guidance-matrix candidate carries an `argv_template` that references CLI-owned envelope fields such as `log_range`
- **AND** those fields are present on the response being annotated
- **THEN** the emitted `argv` includes the concrete values from those fields
- **AND** candidate selection for that response remains identical to any other response with the same command and status
