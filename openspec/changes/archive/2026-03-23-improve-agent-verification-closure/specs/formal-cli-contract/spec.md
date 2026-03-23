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

### Requirement: Project-scoped exec startup continuity stays inside the accepted request lifecycle
For project-scoped work, the formal CLI SHALL treat slow startup or readiness recovery as part of the accepted `exec` request lifecycle once the CLI has taken responsibility for starting or recovering Unity for that request. The normal caller path SHALL remain `exec` followed by `wait-for-exec`, rather than requiring a separate readiness command as the expected recovery branch for ordinary task execution.

#### Scenario: Project-scoped exec is still waiting on startup progress
- **WHEN** a caller invokes `unity-puer-exec exec --project-path ...`
- **AND** Unity startup or project recovery is still progressing for that request
- **THEN** the response prefers a non-terminal accepted state such as `running`
- **AND** the response includes the accepted `request_id`
- **AND** the caller can continue with `wait-for-exec --request-id ...` instead of being told the request already failed

#### Scenario: Project-scoped exec startup truly fails before recovery is possible
- **WHEN** a caller invokes `unity-puer-exec exec --project-path ...`
- **AND** Unity launch or project recovery reaches a true terminal failure rather than in-progress startup
- **THEN** the CLI may still return a terminal startup failure such as `unity_start_failed` or `launch_conflict`
- **AND** the contract does not require automatic retry

### Requirement: Accepted project-scoped exec responses include an explicit continuation hint
When a project-scoped `exec` response enters a non-terminal accepted state, the formal CLI SHALL make the next action explicit enough for a medium-capability agent to follow directly. The default accepted response SHOULD include a machine-usable continuation hint, and the preferred continuation for project-scoped execution SHALL point to `wait-for-exec` with the same `request_id`.

#### Scenario: Caller receives a running project-scoped exec response
- **WHEN** `unity-puer-exec exec --project-path ...` returns `status = "running"`
- **THEN** the response includes the accepted `request_id`
- **AND** the response includes an explicit continuation hint for `wait-for-exec`
- **AND** the continuation hint is concrete enough to show the intended selector and `request_id`, rather than only saying “wait” in general terms

#### Scenario: Continuation hint stays machine-usable and separate from script result data
- **WHEN** a project-scoped `exec` response includes a continuation hint
- **THEN** the hint lives in a top-level response field rather than inside script-authored `result`
- **AND** the hint includes the preferred follow-up command identity
- **AND** the hint includes a full argv form that a caller can follow directly
