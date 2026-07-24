# Project Control Endpoint Specification

## Purpose

Define the Unity-side project control endpoint contract, including dynamic loopback port selection, health identity fields, and project-local session artifact validation rules, so that multiple Unity Editors loading the package can run concurrently without contending for a single fixed port.
## Requirements
### Requirement: Unity control service selects an available loopback port

The Unity-side project control service SHALL bind to a loopback HTTP endpoint by trying the preferred port first and then trying later ports in a bounded range when the preferred port is unavailable. The bound port SHALL be the authoritative service port for that Editor session. Rollover to a later candidate port SHALL occur whenever a bind attempt fails because the candidate port is already in use, regardless of which concrete exception type the host runtime raises for that condition (including a `SocketException` with `SocketError.AddressAlreadyInUse` under Unity's Mono runtime, as well as an `HttpListenerException`). The scan SHALL abort early only on a genuinely fatal error that is not a port-in-use condition.

#### Scenario: Preferred port is available

- **WHEN** a Unity Editor loads the package and the preferred control port is available
- **THEN** the control service binds the preferred loopback endpoint
- **AND** the health endpoint reports that selected port

#### Scenario: Preferred port is occupied

- **WHEN** a Unity Editor loads the package and another process already owns the preferred control port
- **THEN** the control service tries later loopback ports until an available port is bound or the configured range is exhausted
- **AND** it does not fail solely because the preferred port was unavailable

#### Scenario: Host runtime raises a socket-level port-in-use error

- **WHEN** a candidate port is already in use and the host runtime surfaces the conflict as a `SocketException` (Mono) rather than an `HttpListenerException`
- **THEN** the control service treats it as a port-in-use condition and continues to the next candidate port
- **AND** it does not abort the bounded scan after only the first occupied port

#### Scenario: Bounded range is exhausted

- **WHEN** every port in the bounded range is already in use
- **THEN** the control service reports a failure that reflects the full range it attempted
- **AND** the failure does not occur while later ports in the range were still untried

### Requirement: Health response exposes endpoint identity

The Unity-side health endpoint SHALL expose enough identity for a project-scoped caller to verify endpoint ownership and installation consistency, and to observe the Editor without inferring where it writes. A ready health response SHALL include the selected port, base URL, Unity process id when available, resolved Unity project path, session marker, the bridge package version, and the Editor's own console log path. The bridge version SHALL be resolved from the Unity package metadata for the assembly providing the service, and SHALL be omitted or reported as null when that assembly does not belong to an installed package rather than reported as a guessed value. The console log path SHALL be resolved from the running Editor's own Unity runtime, and SHALL be omitted or reported as null when it cannot be resolved rather than reported as a platform-default guess.

The same identity SHALL be available to a caller that has not yet connected, through the endpoint publication defined by `editor-session-discovery`, so that reaching the service never requires probing candidate ports to discover which one belongs to the target project.

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

### Requirement: Control service runs only in the interactive Editor process

The Unity-side control service SHALL start only when activation has been explicitly requested for the running process, under the uniform activation rule defined by `editor-session-discovery`. A non-interactive Unity subprocess such as a batch-mode asset-import worker SHALL NOT request activation implicitly, so that transient subprocesses never contend for or occupy the preferred control port reserved for a controlled Editor.

#### Scenario: Interactive Editor launched with activation requested

- **WHEN** the package loads in an interactive Unity Editor process that was launched with activation requested
- **THEN** the control service starts and binds a loopback endpoint

#### Scenario: Interactive Editor launched without activation requested

- **WHEN** the package loads in an interactive Unity Editor process that was launched without activation requested
- **THEN** the control service does not start
- **AND** the process does not bind or occupy any port in the control port range

#### Scenario: Batch-mode asset-import worker loads the package

- **WHEN** the package loads in a batch-mode Unity subprocess (for example an asset-import worker)
- **THEN** the control service does not start
- **AND** the subprocess does not bind or occupy any port in the control port range

