## ADDED Requirements

### Requirement: A wait-for-exec continuation requires a record, not a template

Whether a response offers `wait-for-exec --request-id` as a continuation SHALL depend on whether the addressed service holds a record for that `request_id`, not on whether the CLI can construct the invocation. When a record exists the candidate SHALL be offered for every selector, omitting `argv` rather than being removed when the selector arguments cannot be filled. When no record exists the CLI SHALL offer no such candidate.

#### Scenario: An accepted base-url request keeps its continuation without argv

- **WHEN** `exec --base-url ...` returns `running` for a request the service accepted
- **THEN** the response includes a `wait-for-exec` candidate with a `when` hint
- **AND** that candidate carries a complete `argv` using the `--base-url` selector when the
  context can fill it
- **AND** it omits `argv` rather than being removed when it cannot

#### Scenario: A request the service never accepted offers no such candidate

- **WHEN** a response describes a request the addressed service holds no record for
- **THEN** the response offers no `wait-for-exec --request-id` candidate
- **AND** any continuation it does offer converges on the script result rather than answering
  `missing`

## MODIFIED Requirements

### Requirement: Incomplete log_range drops argv but keeps the candidate

Candidate presence is determined by command and status alone, except for a continuation that the addressed service cannot honor: a candidate requiring a record for the addressed `request_id` SHALL be omitted when no such record exists. Apart from that case, missing `log_range` or selector context SHALL cause the entry to omit `argv` while still carrying `command` and `when`, rather than removing the candidate or substituting a different command.

#### Scenario: Incomplete log_range drops argv but keeps the candidate

- **WHEN** one of the covered commands returns `status = "completed"` without both `log_range.start` and `log_range.end`
- **THEN** the `get-log-briefs` candidate is still present with `command` and `when`
- **AND** that candidate omits `argv`

#### Scenario: A missing selector omits argv but keeps the candidate

- **WHEN** a continuation candidate's `argv` cannot be filled because the selector context is
  absent, and the addressed service does hold a record for the request
- **THEN** the candidate is still present with `command` and `when`
- **AND** it omits `argv` rather than being removed or replaced by another command