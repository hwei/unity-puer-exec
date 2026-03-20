## MODIFIED Requirements

### Requirement: Exec responses expose a recoverable request identity

The formal CLI SHALL expose a public `request_id` for each accepted `exec` attempt so callers can reason about timeout recovery without depending only on transport success or script-authored correlation data. The CLI SHALL generate a fresh `request_id` automatically for normal use and SHALL also allow the caller to supply an explicit `--request-id` for recovery or idempotent replay.

#### Scenario: Caller receives an accepted exec response

- **WHEN** a caller invokes `unity-puer-exec exec ...` and the request is accepted by the execution service
- **THEN** the response includes a public top-level `request_id` that can be used for later recovery or observation
- **AND** the request identity is part of the formal CLI contract rather than an internal-only detail

#### Scenario: Caller omits an explicit request identity

- **WHEN** a caller invokes `unity-puer-exec exec ...` without `--request-id`
- **THEN** the CLI generates a fresh `request_id` before submission
- **AND** the effective `request_id` is still returned in the accepted response

### Requirement: Exec request identity is caller-owned and idempotent

The formal CLI SHALL treat `request_id` as a caller-owned idempotency key for top-level `exec`. Reusing the same `request_id` with an equivalent execution request SHALL recover or replay the same request state without duplicate execution. Reusing the same `request_id` with a materially different execution request SHALL fail explicitly.

#### Scenario: Caller idempotently replays the same exec request

- **WHEN** a caller invokes `unity-puer-exec exec ... --request-id R` more than once with equivalent execution content and target identity
- **THEN** the service does not start a second execution for `R`
- **AND** the response reports the current or final state of the existing request instead of duplicating side effects

#### Scenario: Caller reuses a request identity for different execution content

- **WHEN** a caller invokes `unity-puer-exec exec ... --request-id R` after `R` has already been associated with materially different execution content or target identity
- **THEN** the command returns a machine-readable `request_id_conflict` result
- **AND** the caller can branch on that result without guessing which request definition won

#### Scenario: Equivalent exec requests ignore CLI input-form differences

- **WHEN** two `exec` attempts use the same effective target identity and the same normalized script content but arrive through different input forms such as `--file`, `--stdin`, or `--code`
- **THEN** the service treats them as the same execution request for `request_id` matching
- **AND** request equivalence is not broken only because the CLI transport form changed

### Requirement: Exec timeout handling distinguishes retry from recovery

The formal CLI SHALL define how callers distinguish between safe retry and recovery-oriented follow-up after `exec` returns `not_available`, transport timeout, `running`, or another ambiguous non-terminal condition.

#### Scenario: Caller hits an ambiguous exec timeout

- **WHEN** `unity-puer-exec exec ...` ends in a transport-level timeout or equivalent ambiguous availability failure
- **AND** the caller knows the `request_id` used for that attempt
- **THEN** the published contract explains that the caller should recover with the same `request_id` rather than blindly starting a fresh request
- **AND** the published contract explains how to recover or query the state of a possibly accepted request

#### Scenario: Caller intentionally starts a new request after ambiguity

- **WHEN** a caller chooses a fresh `request_id` after an ambiguous timeout on a side-effecting script
- **THEN** the published contract treats that action as a new execution attempt rather than as recovery
- **AND** help warns that doing so may duplicate side effects if the original request had already been accepted

### Requirement: Exec exposes a single-active-request contract

The formal CLI SHALL expose at most one active top-level `exec` request at a time. The service SHALL not silently queue a second different top-level request while another one is still active.

#### Scenario: Different request arrives while another exec request is active

- **WHEN** the execution service already has an active top-level `exec` request for `request_id = A`
- **AND** the caller submits a new top-level `exec` request with a different `request_id = B`
- **THEN** the command returns a machine-readable `busy` result
- **AND** the service does not hide the conflict behind an implicit queue

### Requirement: Wait-for-exec continues an accepted request by request identity

The formal CLI SHALL provide a dedicated `wait-for-exec` follow-up surface that continues or queries an accepted request by `request_id` without resubmitting script content.

#### Scenario: Caller follows up on a running request

- **WHEN** a caller invokes `unity-puer-exec wait-for-exec --request-id R`
- **THEN** the command reports the current known state of `R` using `running`, `completed`, or `failed`
- **AND** the caller does not need to resend the original script body

#### Scenario: Caller follows up on a missing request

- **WHEN** a caller invokes `unity-puer-exec wait-for-exec --request-id R` and the addressed service has no recoverable record for `R`
- **THEN** the command returns a machine-readable `missing` result
- **AND** the contract does not require the service to distinguish whether `R` was never accepted, was lost with a replaced service instance, or aged out of retention

### Requirement: Help explains execution identity and observation roles clearly

Top-level and per-command help SHALL explain the distinct roles of public exec `request_id`, script-provided `correlation_id`, and `log_offset`, including how they participate in timeout recovery, idempotent replay, and result observation.

#### Scenario: Agent reads help for timeout-recovery workflow

- **WHEN** an agent reads `unity-puer-exec --help`, `exec --help`, or the relevant published examples
- **THEN** the help distinguishes request-acceptance recovery from later result observation
- **AND** the help explains when retry is safe versus when the caller should continue through recovery-oriented observation
- **AND** the help explains that `request_id` tracks the exec request itself while `correlation_id` remains script-defined observation metadata
