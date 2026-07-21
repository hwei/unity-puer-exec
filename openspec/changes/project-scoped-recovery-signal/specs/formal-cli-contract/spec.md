## ADDED Requirements

### Requirement: Recovery-vs-launch decisions are project-scoped

When a project-scoped command finds no ready, project-matched endpoint (via session artifact validation or range-scan discovery) and must decide whether to wait for a recovering Editor or launch a new one, that decision SHALL be based only on signals scoped to the requested project — the session artifact's own recorded process, and the requested project's own lock state — never on the presence of Unity Editor processes belonging to other projects.

#### Scenario: Unrelated project running does not block launching the requested project

- **WHEN** a project-scoped command runs for a requested project that has no session artifact and is not yet running
- **AND** a different, unrelated project's Editor is already running on the host, holding no lock on the requested project's own project directory
- **THEN** the command does not treat the unrelated project's process as a reason to wait
- **AND** it proceeds to launch a new Unity Editor for the requested project instead of waiting for a recovery that will never happen

#### Scenario: Requested project's own lock in use is still recognized as recoverable

- **WHEN** a project-scoped command runs for a requested project whose own project lock is currently held by another process (e.g. an Editor for that exact project starting or already open, not yet exposing a matched `/health` response)
- **THEN** the command treats this as a recoverable signal
- **AND** it waits for the project's endpoint to become ready instead of attempting a duplicate launch that would conflict with Unity's own project-lock enforcement
