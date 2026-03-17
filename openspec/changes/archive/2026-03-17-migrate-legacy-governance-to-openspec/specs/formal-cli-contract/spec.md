## ADDED Requirements

### Requirement: The CLI exposes one primary entry and flat command tree

The formal CLI SHALL use `unity-puer-exec` as its single primary entry. The authoritative flat command tree SHALL include `wait-until-ready`, `wait-for-log-pattern`, `get-log-source`, `exec`, `get-result`, and `ensure-stopped`.

#### Scenario: Contributor documents the CLI surface

- **WHEN** repository documentation or help describes the product CLI
- **THEN** `unity-puer-exec` is presented as the primary entry
- **AND** transitional aliases such as `unity-puer-session` are not presented as the long-lived authoritative surface

### Requirement: Command addressing uses mutually exclusive selectors

Selector-driven commands SHALL accept exactly one of `--project-path` or `--base-url`. Supplying both MUST be treated as a usage error, and project path resolution MUST follow the repository's deterministic resolution order.

#### Scenario: Caller supplies both selectors

- **WHEN** a selector-driven command receives both `--project-path` and `--base-url`
- **THEN** the command reports a usage error
- **AND** machine-readable structured output surfaces the `address_conflict` state when applicable

### Requirement: Async continuation is token-driven

`exec` SHALL remain selector-driven, while `get-result` SHALL be driven only by `--continuation-token`. The continuation token MUST carry enough opaque routing and continuity information to validate that the caller is polling the originating execution-service lifetime.

#### Scenario: Running execution returns a continuation token

- **WHEN** `exec` finishes in the `running` state
- **THEN** the result includes `continuation_token`
- **AND** later `get-result` calls use that token instead of selector inputs

#### Scenario: Continuation session is no longer valid

- **WHEN** `get-result` reaches a service that no longer matches the originating continuation session
- **THEN** the command reports `session_missing` or `session_stale`
- **AND** the command does not silently create a replacement session

### Requirement: Formal command results are machine-readable JSON on stdout

All formal command results SHALL be machine-readable JSON. Successes and expected machine states that an agent can branch on MUST appear on stdout, while unstructured usage text or unexpected process-level diagnostics may appear on stderr.

#### Scenario: Agent invokes a formal CLI command

- **WHEN** a formal command completes with success or an expected branchable machine state
- **THEN** stdout contains the authoritative JSON payload
- **AND** the payload includes stable top-level fields needed by that command family

### Requirement: The help surface is agent-discoverable

Top-level and per-command help SHALL describe the single-entry model, selector rules, key workflows, expected success and non-success states, and minimal invocation examples without requiring repository skill documentation as the primary discovery path.

#### Scenario: Agent reads CLI help to discover usage

- **WHEN** an agent runs `unity-puer-exec --help` or a per-command `--help`
- **THEN** the help text explains the command purpose, inputs, machine-state outcomes, and example invocations
- **AND** the agent can discover the normal `exec` and `get-result` workflow from help alone

