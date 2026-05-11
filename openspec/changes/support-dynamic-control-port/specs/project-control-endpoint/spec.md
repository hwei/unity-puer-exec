## ADDED Requirements

### Requirement: Unity control service selects an available loopback port

The Unity-side project control service SHALL bind to a loopback HTTP endpoint by trying the preferred port first and then trying later ports in a bounded range when the preferred port is unavailable. The bound port SHALL be the authoritative service port for that Editor session.

#### Scenario: Preferred port is available

- **WHEN** a Unity Editor loads the package and the preferred control port is available
- **THEN** the control service binds the preferred loopback endpoint
- **AND** the health endpoint reports that selected port

#### Scenario: Preferred port is occupied

- **WHEN** a Unity Editor loads the package and another process already owns the preferred control port
- **THEN** the control service tries later loopback ports until an available port is bound or the configured range is exhausted
- **AND** it does not fail solely because the preferred port was unavailable

### Requirement: Health response exposes endpoint identity

The Unity-side health endpoint SHALL expose enough identity for a project-scoped caller to verify endpoint ownership. A ready health response SHALL include the selected port, base URL, Unity process id when available, resolved Unity project path, and session marker.

#### Scenario: Caller probes a ready service

- **WHEN** a caller probes `/health` on a ready UnityPuerExec service
- **THEN** the response includes `status = "ready"`
- **AND** the response includes `port`, `base_url`, `unity_pid`, `project_path`, and `session_marker`

#### Scenario: Caller compares endpoint ownership

- **WHEN** a caller has a target project path and receives a ready health response from a candidate endpoint
- **THEN** the caller can compare the health `project_path` with the target project path
- **AND** a mismatch identifies the candidate endpoint as not owned by the target project

### Requirement: Project session artifact records validated endpoint identity

The project-local session artifact SHALL record the validated control endpoint identity after a project-scoped session becomes ready. The artifact SHALL include the selected base URL, port, Unity process id when available, session marker, effective log path when known, and resolved project path.

#### Scenario: Readiness is confirmed

- **WHEN** the CLI confirms that a project-scoped UnityPuerExec service is ready and belongs to the target project
- **THEN** the project-local session artifact records the selected endpoint identity
- **AND** later project-scoped commands can use the artifact as a candidate routing hint

#### Scenario: Artifact survives process exit

- **WHEN** a session artifact remains after the Unity process exits or the recorded endpoint is reused by another project
- **THEN** the artifact alone is not sufficient proof that the endpoint is valid
- **AND** a caller must validate live health identity before treating the endpoint as authoritative
