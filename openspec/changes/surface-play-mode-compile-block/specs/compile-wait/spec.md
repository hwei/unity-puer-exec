## ADDED Requirements

### Requirement: Wait-for-compile reports a compile blocked by play mode

When `wait-for-compile` finds no compile in progress, a compile-triggering change pending, and the Editor in play mode, it SHALL return a distinct `compile_blocked` outcome naming play mode as the reason, rather than `no_compile_observed`. The command SHALL NOT spend the full appear window waiting for a compile that cannot start. The outcome SHALL be non-terminal for the compile: it says nothing about whether the pending change compiles.

#### Scenario: Pending change while the Editor is in play mode

- **WHEN** a caller invokes `wait-for-compile`
- **AND** the Editor is in play mode
- **AND** a compile-triggering change is pending
- **AND** no compile is in progress
- **THEN** the command returns `result.status: "compile_blocked"` with `compile_observed: false`
- **AND** the result names `play_mode` as the reason
- **AND** the command returns without waiting out the appear window

#### Scenario: Nothing pending while the Editor is in play mode

- **WHEN** a caller invokes `wait-for-compile`
- **AND** the Editor is in play mode
- **AND** no compile-triggering change is pending
- **THEN** the command keeps its existing outcomes, including `no_compile_observed`
- **AND** it does not report `compile_blocked`

#### Scenario: Compile already in progress during play mode

- **WHEN** a caller invokes `wait-for-compile`
- **AND** the Editor already reports `compiling` while in play mode
- **THEN** the command waits for that compile cycle to settle as it does outside play mode
