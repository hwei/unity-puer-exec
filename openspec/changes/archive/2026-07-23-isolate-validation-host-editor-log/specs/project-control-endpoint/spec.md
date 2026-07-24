## MODIFIED Requirements

### Requirement: Health response exposes endpoint identity

The Unity-side health endpoint SHALL expose enough identity for a project-scoped caller to verify endpoint ownership and installation consistency, and to observe the Editor without inferring where it writes. A ready health response SHALL include the selected port, base URL, Unity process id when available, resolved Unity project path, session marker, the bridge package version, and the Editor's own console log path. The bridge version SHALL be resolved from the Unity package metadata for the assembly providing the service, and SHALL be omitted or reported as null when that assembly does not belong to an installed package rather than reported as a guessed value. The console log path SHALL be resolved from the running Editor's own Unity runtime, and SHALL be omitted or reported as null when it cannot be resolved rather than reported as a platform-default guess.

#### Scenario: Caller probes a ready service

- **WHEN** a caller probes `/health` on a ready UnityPuerExec service
- **THEN** the response includes `status = "ready"`
- **AND** the response includes `port`, `base_url`, `unity_pid`, `project_path`, `session_marker`, `bridge_version`, and `console_log_path`

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

#### Scenario: Service assembly is not package-installed

- **WHEN** the Editor assembly providing the service does not belong to an installed Unity package
- **THEN** the health response omits `bridge_version` or reports it as null
- **AND** the response remains otherwise well-formed so callers can still evaluate endpoint ownership

#### Scenario: Console log path cannot be resolved

- **WHEN** the bridge cannot resolve the Editor's console log path
- **THEN** the health response omits `console_log_path` or reports it as null
- **AND** the response remains otherwise well-formed so callers can still evaluate endpoint ownership
