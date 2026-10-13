## MODIFIED Requirements

### Requirement: Play-mode commands recover a dropped control endpoint

When a play-mode request cannot be delivered because the control endpoint dropped — for
example an empty or unparseable response body during a domain reload, or a connection the
endpoint reset before answering — each play-mode command SHALL re-resolve the endpoint and
retry the request within its bound. If the endpoint does not recover within the bound, the
command SHALL report the structured non-success state that names the condition, with its
formal exit code, instead of collapsing it into a generic failure. When the drop was a
connection reset, the underlying transport detail (for example the reset errno) SHALL remain
visible in the reported payload so the condition is recognizable when it recurs.

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

#### Scenario: Endpoint resets mid-transition and recovers

- **WHEN** a play-mode request reaches a control endpoint that accepts the connection and then resets it before sending a response, and the Editor's endpoint becomes reachable again within the command's budget
- **THEN** the command re-resolves the endpoint and retries the request
- **AND** it does not report the reset as a terminal or generic failure

#### Scenario: Endpoint keeps resetting for the whole bound

- **WHEN** the control endpoint resets every attempt for the whole command budget
- **THEN** the process exits with the formal exit code for the not-available condition rather than a generic failure code
- **AND** the reported payload names the endpoint as unreachable or not answering
- **AND** the payload still carries the underlying reset detail for diagnosis