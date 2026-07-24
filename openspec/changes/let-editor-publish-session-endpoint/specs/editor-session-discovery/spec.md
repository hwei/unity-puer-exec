## ADDED Requirements

### Requirement: The Editor publishes its own endpoint

When the Unity control service becomes reachable, the Editor SHALL publish a description of itself at a deterministic path private to its project, so that locating a project's session requires no port scan, no process-table correlation, and no record written by a party other than the Editor.

Every published field SHALL be taken from the running Editor process itself. The publication SHALL include the bound port, the Editor process id, the resolved project path, the session marker, and the Editor's own console log path. No party other than the Editor SHALL write this publication.

The publication is Editor-authored by design, not as a convenience of implementation. A CLI-written session record about a process the CLI does not own can record a recycled process id (any image, not just Unity), a log path guessed at write time, or another project's identity taken from machine-wide process-list order. An Editor-authored publication cannot, because every field is taken from the running process itself (`Process.GetCurrentProcess().Id`, `Application.dataPath`, `Application.consoleLogPath`). No later change SHALL restore CLI-side writing of this record as a shortcut for discovery or recovery.

The publication SHALL remain in place across domain reloads and SHALL be removed only when the Editor process ends, so that a script compile never reads as a withdrawn opt-in.

#### Scenario: A reachable service publishes where and what it is

- **WHEN** the control service binds successfully
- **THEN** the Editor publishes its port, process id, project path, session marker, and console log path
- **AND** a caller can reach the service using the published port without probing any other port

#### Scenario: The publication is not authored by the CLI

- **WHEN** the CLI needs a project's endpoint identity
- **THEN** it reads the Editor's publication rather than writing or maintaining a record of its own
- **AND** no CLI-authored session record participates in endpoint resolution

#### Scenario: A partially written publication is never observed

- **WHEN** a caller reads the publication while the Editor is writing it
- **THEN** the caller observes either the previous complete content or the new complete content
- **AND** it never observes a truncated or partial record

#### Scenario: The publication survives a domain reload

- **WHEN** the Editor recompiles scripts and the control service restarts within the same process
- **THEN** the publication remains present throughout
- **AND** it names the currently bound port once the service is reachable again

### Requirement: Session state is decided from project-local files

The CLI SHALL decide whether a project has a controllable Editor from project-local state alone: the project's Unity lockfile and the Editor's published endpoint. It SHALL NOT infer a project's session state from a machine-wide process listing, and SHALL NOT treat a recorded process id as evidence that a session is live.

A present publication is a claim to verify, not a conclusion: before treating a session as controlled, the CLI SHALL confirm that the published endpoint answers and reports the identity the publication names. A publication that is unreachable or does not match SHALL be treated as residue.

#### Scenario: No Editor is running

- **WHEN** the project lockfile is not held and no endpoint is published
- **THEN** the CLI reports that no Editor is running for the project
- **AND** a launch-driven command proceeds to launch one

#### Scenario: An Editor is running but did not opt in

- **WHEN** the project lockfile is held and no endpoint is published
- **THEN** the CLI reports that an Editor is running without a control service
- **AND** it does not attach to any endpoint on the caller's behalf

#### Scenario: A controlled Editor is present

- **WHEN** the project lockfile is held and an endpoint is published
- **AND** the published endpoint answers with an identity matching the publication
- **THEN** the CLI connects to the published endpoint directly

#### Scenario: A stale publication does not impersonate a controlled session

- **WHEN** the project lockfile is held and a publication is present
- **AND** the published endpoint is unreachable or answers with an identity that does not match the publication
- **THEN** the CLI treats the publication as residue
- **AND** it reports the running Editor as not under CLI control rather than adopting the published endpoint

#### Scenario: A service restart window is not a missing opt-in

- **WHEN** the project lockfile is held and the publication or its service is momentarily unavailable while the Editor's service restarts across a domain reload
- **THEN** the CLI allows for the restart window before concluding that the Editor did not opt in

#### Scenario: Residue from a crashed or killed Editor

- **WHEN** an endpoint is published but the project lockfile is not held
- **THEN** the CLI reports the session as ended rather than attempting to use the published port
- **AND** the published console log path remains readable for post-mortem observation

#### Scenario: An unrelated project's Editor is not consulted

- **WHEN** other Unity Editor processes are running on the machine for other projects
- **THEN** they do not affect the reported session state of the target project
- **AND** no command targets a process belonging to another project

### Requirement: Control-service activation is explicit and uniform

The control service SHALL start only when activation is explicitly requested, and the same rule SHALL apply to every launch mode, including CLI-driven launches, batch-mode processes, and Editors a human opened directly. A process that was not launched with activation requested SHALL be able to activate the service for the remainder of its own lifetime through an Editor-side action.

An activation granted after process start SHALL NOT persist beyond the Editor process that granted it.

#### Scenario: Activation requested at launch

- **WHEN** a Unity process is launched with control-service activation requested
- **THEN** the control service starts
- **AND** it remains active across domain reloads for the lifetime of that process

#### Scenario: Activation not requested

- **WHEN** a Unity process is launched without control-service activation requested
- **THEN** the control service does not start
- **AND** no port in the control port range is bound by that process

#### Scenario: Batch-mode follows the same rule

- **WHEN** a batch-mode Unity process is launched without activation requested
- **THEN** the control service does not start
- **AND** the outcome is decided by the same activation rule as an interactive process, not by a mode-specific exception

#### Scenario: Batch-mode with activation starts the service

- **WHEN** a batch-mode Unity process is launched with activation requested
- **THEN** the control service starts
- **AND** the process binds a port in the control port range

#### Scenario: Activation after process start

- **WHEN** an operator activates the control service from the Editor in a process that was launched without activation
- **THEN** the service starts and publishes its endpoint
- **AND** the activation survives domain reloads within that process
- **AND** the activation is not restored when the project is next opened

### Requirement: A session that cannot be observed safely says so before it is observed

When a controllable Editor's console log path is the platform default per-user log, the CLI SHALL report the session's observation reliability before a caller takes byte offsets against it, because such a log can be shared, rotated, or truncated by an Editor belonging to another project.

#### Scenario: Controlled Editor with a project-private log

- **WHEN** the published console log path is private to the project
- **THEN** the CLI reports observation as reliable

#### Scenario: Controlled Editor with a caller-directed log

- **WHEN** the published console log path is a location the caller chose explicitly at launch, distinct from the platform default
- **THEN** the CLI reports observation as reliable
- **AND** it attributes the location to the caller's explicit choice rather than to a platform guess

#### Scenario: Editor bound to the shared per-user log while another Editor runs

- **WHEN** the published console log path is the platform default per-user log
- **AND** another Unity Editor process is running on the machine
- **THEN** the CLI reports that byte-offset observation of this session is unreliable
- **AND** it does so before the caller takes offsets rather than only after offsets are invalidated

#### Scenario: Editor bound to the shared per-user log as the only Editor

- **WHEN** the published console log path is the platform default per-user log
- **AND** no other Unity Editor process is running on the machine
- **THEN** the CLI reports the session as usable
- **AND** it still identifies the log as one the session does not privately own
