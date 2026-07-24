## ADDED Requirements

### Requirement: Parse-level usage failures emit the machine-readable envelope

A usage failure detected while parsing arguments SHALL produce the same machine-readable JSON envelope as a usage failure detected after parsing. The CLI SHALL NOT emit an unstructured argument-parser usage block as the sole response to a rejected invocation.

#### Scenario: Unrecognized option produces JSON

- **WHEN** a caller passes an option the invoked command does not accept
- **THEN** the response is a JSON payload carrying `ok`, `status`, and `error`
- **AND** the process exits with code `2`
- **AND** no bare argument-parser usage block is emitted as the response

#### Scenario: Missing required argument produces JSON

- **WHEN** a caller omits an argument the invoked command requires
- **THEN** the response is a JSON payload carrying `ok`, `status`, and `error`
- **AND** the process exits with code `2`

#### Scenario: Rejected invocation before any command work

- **WHEN** an invocation is rejected at the parse layer
- **THEN** no Unity service is contacted and no command work is performed

### Requirement: Parse-level usage failures report status invalid_arguments

The CLI SHALL report `invalid_arguments` as the status for a usage failure detected at the parse layer, distinguishing it from `failed`, which denotes an unexpected execution failure. The exit code SHALL remain `2`.

#### Scenario: Status distinguishes usage from execution failure

- **WHEN** an invocation is rejected at the parse layer
- **THEN** the response status is `invalid_arguments`
- **AND** the status is not `failed`
- **AND** the exit code is `2` rather than `1`

#### Scenario: Status is documented once for the CLI

- **WHEN** a caller consults help for usage-failure behavior
- **THEN** `invalid_arguments` and its exit code are documented as a CLI-wide usage status

### Requirement: Usage failures identify the invoked command and its help tier

A usage-failure response SHALL name the command the caller was invoking, when a command is identifiable from the invocation, and SHALL direct the caller to that command's argument help rather than to the top-level command list.

#### Scenario: Unrecognized option on a subcommand

- **WHEN** a caller passes an unrecognized option to a recognized command
- **THEN** the response names that command
- **AND** the response directs the caller to that command's argument help
- **AND** the response does not present only the top-level list of command names

#### Scenario: No recognizable command in the invocation

- **WHEN** an invocation contains no recognizable command token
- **THEN** the response reports the failure at the top-level surface
- **AND** directs the caller to top-level help

### Requirement: Usage failures suggest a near-matching option when one exists

When a rejected option string closely resembles an option that the invoked command does accept, the response SHALL include that near match. When no candidate is sufficiently similar, the response SHALL omit any suggestion rather than offer a weak one.

#### Scenario: Close guess is redirected

- **WHEN** a caller passes `--timeout-ms` to `exec`, which accepts `--wait-timeout-ms`
- **THEN** the response includes `--wait-timeout-ms` as a near match

#### Scenario: Candidates come from the invoked command

- **WHEN** a near match is computed for a rejected option
- **THEN** the candidates are the option strings accepted by the invoked command
- **AND** options belonging only to other commands are not offered

#### Scenario: No sufficiently similar option

- **WHEN** a rejected option resembles no option of the invoked command closely enough
- **THEN** the response omits a near-match suggestion
