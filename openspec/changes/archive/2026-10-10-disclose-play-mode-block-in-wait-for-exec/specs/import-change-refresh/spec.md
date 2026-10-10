## ADDED Requirements

### Requirement: Wait-for-exec discloses a play-mode compile block like exec

When a `wait-for-exec` response covers a request that ran while the Editor was in play mode
with a compile-triggering change pending, the response SHALL carry the same
`compile_blocked` disclosure and warning status as the equivalent `exec` response. A
terminal response SHALL NOT report a plain success in that case. The same precedence rules
apply: a failure status or an existing async warning keeps its status and code, and the
`compile_blocked` object is attached in every case.

#### Scenario: Continued request reports the play-mode block

- **WHEN** an `exec` request is continued with `wait-for-exec`
- **AND** the Editor is in play mode
- **AND** a compile-triggering change was pending when the script ran
- **THEN** the terminal `wait-for-exec` response reports `status: "warning"` with `warning: "compile_blocked_by_play_mode"`
- **AND** it carries a `compile_blocked` object naming `play_mode` as the reason
- **AND** it lists the pending paths when the service knows them

#### Scenario: Recovered failure keeps its status and still carries the object

- **WHEN** the continued request fails
- **AND** a compile-triggering change was pending while the Editor was in play mode
- **THEN** the response keeps the failure status it would report outside play mode
- **AND** it still carries the `compile_blocked` object

#### Scenario: Nothing pending is unchanged

- **WHEN** no compile-triggering change is pending
- **AND** the Editor is in play mode
- **THEN** the `wait-for-exec` response reports the status it reports today
- **AND** it carries no `compile_blocked` object

#### Scenario: Non-terminal response is not rewritten

- **WHEN** `wait-for-exec` returns a non-terminal `running` / `refreshing` response
- **THEN** the response is not annotated with a `compile_blocked` object
