## MODIFIED Requirements

### Requirement: Project-scoped commands validate control endpoint identity

Project-scoped selector commands SHALL discover the Unity control endpoint from project-local session state and live health checks instead of assuming a globally fixed default endpoint. A session artifact endpoint SHALL be treated as a candidate until a live health response proves that the endpoint belongs to the requested project.

When neither a session artifact nor the preferred port yields a ready endpoint owned by the requested project, the CLI SHALL perform an active discovery scan across the bounded control-port range that the Unity control service binds within, probing live `/health` on each candidate and claiming the candidate whose health identity matches the requested project. The scan SHALL try the preferred port first so the single-instance case keeps its fast path, and SHALL stop at the first ready, project-matched endpoint. Range-aware discovery SHALL apply at every project-scoped readiness site — initial discovery, any re-probe after a launch claim, recovery waiting, and the wait that follows a cold-start launch — so the CLI never waits on the preferred port while the project's actual endpoint is a different port in the range. A ready endpoint whose health identity belongs to a different project SHALL never be claimed, on any port.

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

#### Scenario: Target Editor is live on a non-preferred port with no artifact

- **WHEN** a project-scoped command runs and the requested project's Editor is already ready on a non-preferred port in the control-port range
- **AND** no session artifact records that endpoint and the preferred port is owned by a different project or is free
- **THEN** the command discovers the project's endpoint by scanning the control-port range and matching health identity
- **AND** it routes work to that matched endpoint instead of launching a duplicate Editor or timing out on the preferred port

#### Scenario: Recovery waits on the actually-bound port

- **WHEN** a project-scoped command is waiting for a recovering or starting Editor for the requested project
- **AND** that Editor will bind a non-preferred port because the preferred port is unavailable
- **THEN** the readiness wait resolves the endpoint by range scan with health-identity matching rather than waiting only on the preferred port
- **AND** the command binds the session to the resolved endpoint once a ready, project-matched health response appears

#### Scenario: Cold-start launch rolls over off the preferred port

- **WHEN** a project-scoped command launches Unity for the requested project and the preferred port is already in use
- **AND** the launched Editor binds a later port in the control-port range
- **THEN** the post-launch readiness wait discovers the launched Editor by range scan with health-identity matching
- **AND** the command does not report the launched project as not ready merely because the preferred port did not become ready

#### Scenario: Preferred port is occupied by a different, already-ready project with no local artifact

- **WHEN** a project-scoped command runs for a requested project that has no session artifact and is not yet running
- **AND** a different, unrelated project's Editor is already `ready` on the preferred port
- **THEN** the command SHALL NOT treat that endpoint's health identity, `session_marker`, or `base_url` as belonging to the requested project
- **AND** the command SHALL NOT persist a session artifact for the requested project that records the unrelated project's endpoint
- **AND** the command instead continues through the normal launch, recovery, or range-scan discovery flow for the requested project
