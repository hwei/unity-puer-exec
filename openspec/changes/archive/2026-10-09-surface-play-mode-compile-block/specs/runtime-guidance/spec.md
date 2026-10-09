## ADDED Requirements

### Requirement: Play-mode compile block guidance leads out of play mode

Responses that report a compile blocked by play mode, whether the `exec` warning or the `wait-for-compile` `compile_blocked` outcome, SHALL carry a `situation` saying that the pending change will not compile until the Editor leaves play mode. They SHALL carry `next_steps` that exit play mode, confirm it was exited, and then continue the compile cycle. They SHALL NOT suggest forcing a script compilation while play mode continues.

#### Scenario: Agent receives the exec play-mode warning

- **WHEN** an `exec` response reports `warning: "compile_blocked_by_play_mode"`
- **THEN** its `situation` states that the script ran without the pending change and that compilation waits for play mode to exit
- **AND** its `next_steps` include a step that exits play mode
- **AND** its `next_steps` include a follow-up that waits for the resulting compile cycle

#### Scenario: Agent receives the wait-for-compile block outcome

- **WHEN** `wait-for-compile` returns `result.status: "compile_blocked"`
- **THEN** its `situation` states that the compile cannot start while play mode continues
- **AND** its `next_steps` lead out of play mode before retrying the wait
- **AND** neither field suggests `CompilationPipeline.RequestScriptCompilation()` as the remedy

#### Scenario: The new statuses appear in status help

- **WHEN** an agent reads `exec --help-status` or `wait-for-compile --help-status`
- **THEN** the play-mode compile block is listed with its meaning and its way out
