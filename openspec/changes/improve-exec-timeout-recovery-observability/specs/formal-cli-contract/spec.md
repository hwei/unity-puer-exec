## MODIFIED Requirements

### Requirement: Exec responses expose a recoverable request identity

The formal CLI SHALL expose a public request identity for each `exec` attempt so callers can reason about timeout recovery without depending only on transport success or script-authored correlation data.

#### Scenario: Caller receives an accepted exec response

- **WHEN** a caller invokes `unity-puer-exec exec ...` and the request is accepted by the execution service
- **THEN** the response includes a public request identity that can be used for later recovery or observation
- **AND** the request identity is part of the formal CLI contract rather than an internal-only detail

### Requirement: Exec timeout handling distinguishes retry from recovery

The formal CLI SHALL define how callers distinguish between safe retry and recovery-oriented follow-up after `exec` returns `not_available`, transport timeout, or another ambiguous non-terminal condition.

#### Scenario: Caller hits an ambiguous exec timeout

- **WHEN** `unity-puer-exec exec ...` ends in a transport-level timeout or equivalent ambiguous availability failure
- **THEN** the published contract explains whether the caller can safely retry immediately
- **AND** the published contract explains how to recover or query the state of a possibly accepted request

### Requirement: Help explains execution identity and observation roles clearly

Top-level and per-command help SHALL explain the distinct roles of public exec request identity, script-provided `correlation_id`, and `log_offset`, including how they participate in timeout recovery and result observation.

#### Scenario: Agent reads help for timeout-recovery workflow

- **WHEN** an agent reads `unity-puer-exec --help`, `exec --help`, or the relevant published examples
- **THEN** the help distinguishes request-acceptance recovery from later result observation
- **AND** the help explains when retry is safe versus when the caller should continue through recovery-oriented observation
