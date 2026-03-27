## MODIFIED Requirements

### Requirement: Exec timeout handling distinguishes retry from recovery

The formal CLI SHALL define how callers distinguish between safe retry and recovery-oriented follow-up after `exec` returns `not_available`, transport timeout, `running`, or another ambiguous non-terminal condition. When an exec request has already been accepted and remains recoverable, the implementation SHALL prefer graceful transport close behavior over noisy server-side write failures if the original client connection ends before Unity-side work has fully drained.

#### Scenario: Accepted request outlives the original response wait

- **WHEN** a project-scoped or direct-service `exec` request has already been accepted
- **AND** the original client-side wait path ends before the Unity-side work or response-drain path is finished
- **THEN** the request remains recoverable by the same `request_id`
- **AND** the implementation avoids treating the disconnect as the authoritative script outcome
- **AND** benign disconnect handling does not replace later recovery through `wait-for-exec` or log observation
