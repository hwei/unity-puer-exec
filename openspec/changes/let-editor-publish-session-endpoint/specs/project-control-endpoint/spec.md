## REMOVED Requirements

### Requirement: Project session artifact records validated endpoint identity

**Reason**: The artifact was written by the CLI about a process it does not own, and populated its process id from machine-wide tasklist order rather than from the endpoint's own health payload, so it could record an unrelated project's identity. Every field it carried is now published by the Editor about itself under `editor-session-discovery`.

**Migration**: Callers reading `Temp/UnityPuerExec/session.json` read the Editor-published endpoint at `Temp/UnityPuerExec/endpoint.json` instead. The scenario "Artifact survives process exit" is superseded by the residue case in `editor-session-discovery`: the publication is removed with `Temp/` on clean exit, and a publication present without a held project lockfile identifies an ended session rather than a candidate endpoint.

## MODIFIED Requirements

### Requirement: Control service runs only when activation is requested

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
