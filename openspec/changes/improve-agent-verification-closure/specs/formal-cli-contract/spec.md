## ADDED Requirements

### Requirement: Basic project-scoped workflows provide a CLI-native verification closure path
The formal CLI SHALL provide a verification-oriented workflow for basic project-scoped tasks that lets callers confirm success without falling back to direct host-file or host-log inspection as the normal path. For workflows that require delayed observation after `exec`, the CLI SHALL expose or document a preferred machine-usable follow-up path that remains inside the formal CLI surface.

#### Scenario: Caller verifies a basic project-scoped task after exec
- **WHEN** a caller completes a basic project-scoped workflow through `exec` and needs to confirm the outcome
- **THEN** the preferred confirmation path stays within the formal CLI observation surface
- **AND** the normal workflow does not require direct host-file or host-log inspection as the primary verification mechanism

### Requirement: Verification workflows remain usable across compile and observation timing friction
The formal CLI SHALL define a machine-usable verification workflow that remains understandable when delayed editor state changes, compilation, selection timing, or delayed log emission occur after a basic project-scoped `exec`. The preferred workflow SHALL make it possible for callers to recover verification without abandoning the CLI-native observation path.

#### Scenario: Caller encounters delayed verification conditions after exec
- **WHEN** a caller attempts to verify a basic project-scoped workflow and the first confirmation attempt is disrupted by compilation, selection timing, or delayed log emission
- **THEN** the CLI surface still provides a documented recovery path for completing verification
- **AND** the caller does not need to invent an unrelated host-side inspection method to finish the normal verification workflow
