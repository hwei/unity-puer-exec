# Spec Delta

## Purpose

Defines how the `unity-puer-exec` CLI invites agents to report defects and workflow friction to the upstream repository, disclosed progressively so the reporting procedure is only read when something has gone wrong.

## ADDED Requirements

### Requirement: Top-level help carries a one-line feedback pointer
Top-level `unity-puer-exec --help` SHALL include a `Feedback` section of a single bullet that names `unity-puer-exec --help-feedback` as the place to read before reporting a bug or friction. The section SHALL NOT itself contain the reporting procedure or redaction rules.

#### Scenario: Agent reads top-level help
- **WHEN** an agent runs `unity-puer-exec --help`
- **THEN** the output contains a `Feedback` section that references `unity-puer-exec --help-feedback`
- **AND** that section is one bullet long

### Requirement: The CLI answers a --help-feedback topic
`unity-puer-exec --help-feedback` SHALL print the reporting procedure on stdout and exit 0 without contacting Unity and without requiring a selector. Extra arguments after `--help-feedback` SHALL be rejected with a usage error.

#### Scenario: Agent requests the feedback topic
- **WHEN** an agent runs `unity-puer-exec --help-feedback`
- **THEN** the process exits 0 and prints the feedback procedure
- **AND** no Unity session is discovered, launched, or contacted

#### Scenario: Extra arguments are rejected
- **WHEN** an agent runs `unity-puer-exec --help-feedback extra`
- **THEN** the CLI reports a usage error instead of printing the topic

### Requirement: The feedback topic requires user confirmation before filing
The `--help-feedback` content SHALL instruct the agent to describe the proposed report to the user and to file it only after the user explicitly confirms, and SHALL name the issue tracker URL `https://github.com/hwei/unity-puer-exec/issues`.

#### Scenario: Topic states the confirmation gate
- **WHEN** an agent reads `--help-feedback`
- **THEN** the text states that the agent asks the user first and files only after confirmation
- **AND** the text contains `https://github.com/hwei/unity-puer-exec/issues`

### Requirement: The feedback topic requires redaction for a public tracker
The `--help-feedback` content SHALL state that the tracker is public and SHALL instruct the agent to remove project paths, project source code, asset names, and log content the user has not approved for sharing.

#### Scenario: Topic states redaction rules
- **WHEN** an agent reads `--help-feedback`
- **THEN** the text states the tracker is public
- **AND** the text lists project paths, project code, asset names, and unapproved log content as material to remove

### Requirement: The feedback topic requires duplicate search and defines report content
The `--help-feedback` content SHALL instruct the agent to search existing issues before filing and to comment on a matching issue instead of opening a duplicate. It SHALL list the report contents: `unity-puer-exec --version` output, the command line, the response `status` and exit code, expected versus actual behavior, and minimal reproduction steps.

#### Scenario: Topic lists duplicate search and report fields
- **WHEN** an agent reads `--help-feedback`
- **THEN** the text instructs searching existing issues first
- **AND** the text names `--version`, command line, status and exit code, expected versus actual behavior, and reproduction steps

### Requirement: The feedback topic provides a no-gh fallback
The `--help-feedback` content SHALL describe a fallback for when the GitHub CLI is unavailable or unauthenticated: hand the user a prefilled `https://github.com/hwei/unity-puer-exec/issues/new` URL with `title` and `body` query parameters rather than abandoning the report.

#### Scenario: Topic describes the prefilled URL fallback
- **WHEN** an agent reads `--help-feedback`
- **THEN** the text describes giving the user a prefilled `issues/new` URL when `gh` cannot be used

### Requirement: The feedback topic covers friction as well as bugs
The `--help-feedback` content SHALL state that confusing responses, missing or misleading guidance, and clumsy workflows are reportable in addition to defects.

#### Scenario: Topic invites friction reports
- **WHEN** an agent reads `--help-feedback`
- **THEN** the text names friction such as confusing responses or missing guidance as reportable

### Requirement: Failures from uncaught CLI exceptions carry failure_origin cli_internal
When a response is produced by the CLI handler for an exception no more specific handler classified, it SHALL carry the CLI-owned envelope field `failure_origin: "cli_internal"`. The response `status` and exit code SHALL be unchanged (`failed`, exit 1).

#### Scenario: Uncaught exception inside a command
- **WHEN** a command raises an exception that reaches the CLI unclassified-exception handler
- **THEN** the response has `ok: false`, `status: "failed"`, exit code 1
- **AND** the response carries `failure_origin: "cli_internal"`

### Requirement: Service internal errors carry failure_origin service_internal
When the Unity control service reports its own unhandled request failure (HTTP 500 whose body has `error: "internal_error"`), the CLI response SHALL carry `failure_origin: "service_internal"`. Status, `http_status`, and exit code SHALL stay as the CLI already reports them for that HTTP 500.

#### Scenario: Service request handler throws
- **WHEN** the control service answers a request with HTTP 500 and `{"ok":false,"status":"failed","error":"internal_error"}`
- **THEN** the CLI response carries `failure_origin: "service_internal"`
- **AND** its `status` and exit code are unchanged from the HTTP 500 handling that existed before this field

#### Scenario: An HTTP 500 without the internal-error body is not marked
- **WHEN** an endpoint answers HTTP 500 with a body that is absent, not JSON, or has an `error` other than `internal_error`
- **THEN** the CLI response carries no `failure_origin` field

### Requirement: failure_origin is limited to likely tool defects
Outside those two cases the CLI SHALL NOT set `failure_origin`, including for script-authored failures, usage failures, transport or environment states, or other classified non-success statuses, including `invalid_arguments`, `not_available` (other than the service internal-error case), `empty_response`, `unity_start_failed`, `unity_not_ready`, `modal_blocked`, `unity_compile_error`, `version_mismatch`, and `refresh_unsettled`.

#### Scenario: Script error is not classified as a tool defect
- **WHEN** an `exec` script throws and the response has `status: "failed"`
- **THEN** the response carries no `failure_origin` field

#### Scenario: Classified non-success statuses are not marked
- **WHEN** a command returns a classified non-success status such as `not_available`, `invalid_arguments`, or `refresh_unsettled`
- **THEN** the response carries no `failure_origin` field

### Requirement: failure_origin responses carry a feedback hint
When a response carries `failure_origin`, the CLI SHALL append a feedback hint to `situation` and add one `next_steps` candidate whose `argv` is `["unity-puer-exec", "--help-feedback"]`. Candidates the matrix selects for the command and status SHALL remain present. Composition SHALL key only on `failure_origin`, never on script-authored `result`.

#### Scenario: Hint is added to an internal failure
- **WHEN** a response carries `failure_origin`
- **THEN** `situation` includes a sentence suggesting the agent offer the user a report via `--help-feedback`
- **AND** `next_steps` includes a candidate with `argv` `["unity-puer-exec", "--help-feedback"]`
- **AND** the candidates the matrix selects for that command and status are still present

#### Scenario: Responses without failure_origin carry no hint
- **WHEN** a response carries no `failure_origin`
- **THEN** neither `situation` nor `next_steps` references `--help-feedback`

### Requirement: Guidance suppression removes the feedback hint but not failure_origin
Under `--suppress-guidance` the feedback hint and its `next_steps` candidate SHALL be omitted along with all other guidance, while `failure_origin` SHALL still be emitted.

#### Scenario: Suppressed internal failure
- **WHEN** a command run with `--suppress-guidance` produces a `failure_origin` response
- **THEN** the response carries `failure_origin` and no `next_steps` or `situation`
