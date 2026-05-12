## ADDED Requirements

### Requirement: Project-scoped commands validate control endpoint identity

Project-scoped selector commands SHALL discover the Unity control endpoint from project-local session state and live health checks instead of assuming a globally fixed default endpoint. A session artifact endpoint SHALL be treated as a candidate until a live health response proves that the endpoint belongs to the requested project.

#### Scenario: Valid artifact endpoint is reused

- **WHEN** a project-scoped command finds a session artifact with a candidate base URL
- **AND** probing that base URL returns ready health identity for the requested project
- **THEN** the command uses the validated artifact endpoint for project-scoped routing
- **AND** it does not fall back to the fixed preferred port merely because the selected port is different

#### Scenario: Stale artifact endpoint is ignored

- **WHEN** a project-scoped command finds a session artifact whose candidate base URL is unreachable or reports health identity for a different project
- **THEN** the command treats that artifact endpoint as stale for routing
- **AND** it continues through the normal project launch or recovery flow instead of sending work to the wrong Editor

#### Scenario: Cold start waits for the new endpoint

- **WHEN** a project-scoped command launches Unity and an old session artifact already exists
- **THEN** the command does not treat the old artifact endpoint as authoritative during cold start
- **AND** it waits for a live ready health response from the launched or recovered project before persisting the effective endpoint

### Requirement: Direct base-url mode remains explicit

Base-url selector mode SHALL continue to target the caller-supplied endpoint directly. Direct mode SHALL NOT require project artifact validation and SHALL NOT imply Unity launch ownership.

#### Scenario: Caller supplies base-url

- **WHEN** a selector-driven command is invoked with `--base-url <url>`
- **THEN** the command targets that URL directly according to the existing direct-service command boundary
- **AND** it does not rewrite the endpoint from a project-local session artifact
