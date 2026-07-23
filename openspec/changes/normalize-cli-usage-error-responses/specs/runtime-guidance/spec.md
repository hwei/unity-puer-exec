## ADDED Requirements

### Requirement: Usage-failure responses carry guidance toward argument help

Usage-failure statuses SHALL have guidance-matrix coverage. The response SHALL carry a `situation` naming what was rejected, and `next_steps` directing the caller to the argument help for the command that was invoked. The guidance SHALL NOT offer the failed invocation back to the caller as a retry candidate, because re-running an invocation the CLI has already rejected cannot succeed.

#### Scenario: Parse-level failure carries guidance

- **WHEN** a command returns `invalid_arguments`
- **THEN** the response includes a `situation` describing what was rejected
- **AND** `next_steps` includes the invoked command's argument help entry

#### Scenario: Post-parse usage failures carry guidance

- **WHEN** a command returns a usage status raised after parsing, such as `full_text_requires_include` or `address_conflict`
- **THEN** the response includes `situation`, `next_steps`, or both, rather than status and error text alone

#### Scenario: Guidance does not suggest retrying the rejected invocation

- **WHEN** a usage-failure response includes `next_steps`
- **THEN** no candidate re-runs the rejected invocation unchanged

### Requirement: Shell-expansion hint covers the syntax-error form

The existing bare-`puer.`-prefix hint SHALL be extended to the form that shell expansion actually produces. When an `exec` or `wait-for-exec` failure is a syntax error and the invocation supplied inline code through `--code` that carries the signature of a consumed `$` — a member access immediately followed by a call, such as `puer.(` — the response `situation` SHALL include a hint naming shell variable expansion as the likely cause and single quoting or `--file` as the resolution.

The hint SHALL require both conditions together, and SHALL apply only to `--code`, because `--file` and `--stdin` content does not pass through shell interpolation.

#### Scenario: Expanded variable in inline code

- **WHEN** `exec --code` fails with a syntax error and the submitted code contains a member access immediately followed by a call
- **THEN** the response `situation` includes a hint that a shell may have expanded a `$` token
- **AND** the hint names single quoting or `--file` as the resolution

#### Scenario: Ordinary syntax error is not misattributed

- **WHEN** `exec --code` fails with a syntax error and the submitted code carries no expansion signature
- **THEN** no shell-expansion hint is attached

#### Scenario: File and stdin sources are excluded

- **WHEN** an `exec` invocation supplied its script through `--file` or `--stdin` and fails with a syntax error
- **THEN** no shell-expansion hint is attached, regardless of the code's content

#### Scenario: Existing prefix hint is preserved

- **WHEN** a failure reports a bare `$typeof` or `$ref` reference error
- **THEN** the existing missing-`puer.`-prefix hint is still attached
