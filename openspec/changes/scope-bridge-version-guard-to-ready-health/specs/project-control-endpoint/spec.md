## MODIFIED Requirements

### Requirement: Health response exposes endpoint identity

The Unity-side health endpoint SHALL expose enough identity for a project-scoped caller to verify endpoint ownership and installation consistency, and to observe the Editor without inferring where it writes. A ready health response SHALL include the selected port, base URL, Unity process id when available, resolved Unity project path, session marker, the bridge package version, and the Editor's own console log path. The bridge version SHALL be resolved from the Unity package metadata for the assembly providing the service, and SHALL be omitted or reported as null when that assembly does not belong to an installed package rather than reported as a guessed value. When that version is known, a bound non-ready health response (`compiling`, or `not_available` while the control service is listening) SHALL also include `bridge_version`. The console log path SHALL be resolved from the running Editor's own Unity runtime, and SHALL be omitted or reported as null when it cannot be resolved rather than reported as a platform-default guess.

The same identity SHALL be available to a caller that has not yet connected, through the endpoint publication defined by `editor-session-discovery`, so that reaching the service never requires probing candidate ports to discover which one belongs to the target project.

#### Scenario: Caller probes a ready service

- **WHEN** a caller probes `/health` on a ready UnityPuerExec service
- **THEN** the response includes `status = "ready"`
- **AND** the response includes `port`, `base_url`, `unity_pid`, `project_path`, `session_marker`, `bridge_version`, and `console_log_path`

#### Scenario: Caller probes a compiling service

- **WHEN** a caller probes `/health` while the Editor is compiling or reloading and the Editor assembly belongs to an installed package
- **THEN** the response includes `status = "compiling"`
- **AND** the response includes `session_marker`
- **AND** the response includes `bridge_version` set to that package's version

#### Scenario: Caller compares endpoint ownership

- **WHEN** a caller has a target project path and receives a ready health response from a candidate endpoint
- **THEN** the caller can compare the health `project_path` with the target project path
- **AND** a mismatch identifies the candidate endpoint as not owned by the target project

#### Scenario: Caller compares installation consistency

- **WHEN** a caller receives a ready health response and knows its own CLI version
- **THEN** the caller can compare the health `bridge_version` with its own version
- **AND** a difference identifies the two product halves as a mixed installation

#### Scenario: Caller locates the observable log without guessing

- **WHEN** a caller receives a ready health response
- **THEN** `console_log_path` names the log file that Editor process is writing to
- **AND** the caller can observe that path instead of assuming the platform default Editor log

#### Scenario: Caller reaches the service without probing candidate ports

- **WHEN** a caller needs to reach the control service of a specific project
- **THEN** the published endpoint supplies the port to connect to
- **AND** the caller does not probe other ports in the control port range to establish ownership

#### Scenario: Service assembly is not package-installed

- **WHEN** the Editor assembly providing the service does not belong to an installed Unity package
- **THEN** the health response omits `bridge_version` or reports it as null
- **AND** the response remains otherwise well-formed so callers can still evaluate endpoint ownership

#### Scenario: Console log path cannot be resolved

- **WHEN** the bridge cannot resolve the Editor's console log path
- **THEN** the health response omits `console_log_path` or reports it as null
- **AND** the response remains otherwise well-formed so callers can still evaluate endpoint ownership
