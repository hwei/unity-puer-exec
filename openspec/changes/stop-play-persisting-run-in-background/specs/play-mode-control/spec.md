# Spec Delta

## MODIFIED Requirements

### Requirement: Play forces run-in-background by default

`play` SHALL set `Application.runInBackground` to true for the play session it starts, SHALL NOT modify the project's Player Settings, and SHALL disclose the override in its result together with the project's own setting. The `--no-run-in-background` option SHALL leave the project's setting in effect. The disclosure SHALL name that option.

#### Scenario: Default play forces background running

- **WHEN** an agent runs `play` without options
- **THEN** `Application.runInBackground` is true once the Editor reports `playing`
- **AND** the result reports `run_in_background.forced: true` and the project setting
- **AND** the result names `--no-run-in-background` as the way to keep the project setting

#### Scenario: Agent keeps the project setting

- **WHEN** an agent runs `play --no-run-in-background`
- **THEN** `Application.runInBackground` keeps the value the project configures
- **AND** the result reports `run_in_background.forced: false`

#### Scenario: Project settings stay unmodified

- **WHEN** a forced play session starts and ends
- **AND** the Editor then exits
- **THEN** the project's Player Settings asset on disk is byte-identical to its content before the session started
- **AND** the project's run-in-background setting reads back as the value reported in the result's project setting

#### Scenario: Editor exits while a forced session is still playing

- **WHEN** a forced play session is still running
- **AND** the Editor exits without the session first being stopped
- **THEN** the project's Player Settings asset on disk is byte-identical to its content before the session started

#### Scenario: Override survives a domain reload on entering play mode

- **WHEN** entering play mode reloads the script domain
- **THEN** the override is still applied once the Editor reports `playing`
