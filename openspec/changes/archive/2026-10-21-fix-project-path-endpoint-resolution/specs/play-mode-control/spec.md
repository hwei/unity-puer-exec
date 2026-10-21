# Spec Delta

## ADDED Requirements

### Requirement: Play-mode commands follow the project's published endpoint

In project mode, `play`, `pause`, and `stop` SHALL locate the Editor endpoint on every state probe by first confirming the Editor's endpoint publication. They SHALL fall back to an ownership-checked port scan only when the publication cannot be confirmed. This SHALL keep the probe on the project's Editor across the domain reloads that play-mode transitions cause, including when another project's Editor is running on the same machine.

#### Scenario: Stop observes edit mode after the exit's domain reload

- **WHEN** an agent runs `stop --project-path Project` with a relative path and the Editor leaves play mode
- **AND** the exit's domain reload republishes the endpoint with a new session marker
- **THEN** the command observes `play_state: "edit"` from the republished endpoint
- **AND** it returns `status: "completed"` rather than `running`

#### Scenario: Another project's Editor is not probed as the target

- **WHEN** a second project's Editor is ready on the preferred control port
- **AND** an agent runs a play-mode command for the first project
- **THEN** every state probe reads the first project's Editor
- **AND** the second Editor's play state never satisfies the command

### Requirement: An unresolved endpoint is reported distinctly from an unfinished transition

When a play-mode command's budget elapses without any probe reaching the project's own endpoint, the `running` result SHALL say that the endpoint was not resolved. It SHALL NOT report `play_state: null` in a way that reads as the transition still being in progress. When the endpoint was reached, the result SHALL name the target state and the last observed play state.

#### Scenario: Endpoint never resolved within the budget

- **WHEN** no probe during a `stop` reaches an endpoint owned by the target project before the timeout
- **THEN** the command returns `status: "running"` with a result that marks the endpoint as unresolved
- **AND** its guidance names endpoint resolution as the waiting condition rather than the play-mode exit

#### Scenario: Endpoint reached but transition unfinished

- **WHEN** probes reach the project's endpoint but the Editor has not reached the target state before the timeout
- **THEN** the `running` result names the target play state and the last observed play state
