## ADDED Requirements

### Requirement: Play-mode commands recover a dropped control endpoint

When a play-mode request cannot be delivered because the control endpoint dropped — for
example an empty or unparseable response body during a domain reload — each play-mode
command SHALL re-resolve the endpoint and retry the request within its bound. If the
endpoint does not recover within the bound, the command SHALL report the structured
non-success state that names the condition, with its formal exit code, instead of
collapsing it into a generic failure.

#### Scenario: Endpoint drops mid-transition and recovers

- **WHEN** a play-mode request reaches a control endpoint that drops before answering (for example an empty response body) and the Editor's endpoint becomes reachable again within the command's budget
- **THEN** the command re-resolves the endpoint and retries the request
- **AND** it does not report the dropped response as a terminal failure

#### Scenario: Endpoint never recovers within the bound

- **WHEN** the control endpoint stays unreachable for the whole command budget
- **THEN** the command returns the structured non-success state that names the empty/unreachable condition
- **AND** the process exits with that state's formal exit code rather than a generic failure code

#### Scenario: A recognized non-success answer is not retried as a transport drop

- **WHEN** the endpoint answers with a recognized non-success play-mode status such as `invalid_play_state`
- **THEN** the command reports that status without treating it as a dropped endpoint or retrying the request

### Requirement: Play-mode commands preserve formal exit codes for non-success answers

When a play-mode command receives a machine-readable non-success status from the control
endpoint (for example `modal_blocked` or `empty_response`), the process SHALL exit with
that status's formal exit code. It SHALL NOT collapse distinct non-success states into one
generic failure code.

#### Scenario: A blocking dialog preserves its exit code

- **WHEN** the play-mode endpoint reports `modal_blocked`
- **THEN** the `play` / `pause` / `stop` process exits with the formal `modal_blocked` exit code
- **AND** the payload carries the `modal_blocked` status and its blocker details

#### Scenario: Distinct non-success states stay distinguishable

- **WHEN** two different non-success statuses are returned by the play-mode endpoint across invocations
- **THEN** each maps to its own formal exit code
- **AND** the two invocations are distinguishable by exit code alone
