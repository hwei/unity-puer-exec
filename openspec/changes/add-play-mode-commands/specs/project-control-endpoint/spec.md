## ADDED Requirements

### Requirement: Health response exposes the Editor play state

The health endpoint SHALL report the Editor's play state as one of `edit`, `entering`, `playing`, `paused`, or `exiting`, so callers can observe a play-mode transition without running a script. The value SHALL be sampled from the Editor's main thread state.

#### Scenario: Editor in edit mode

- **WHEN** a caller probes `/health` while the Editor is not playing and no transition is requested
- **THEN** the response reports `play_state: "edit"`

#### Scenario: Editor paused in play mode

- **WHEN** a caller probes `/health` while the Editor is playing and paused
- **THEN** the response reports `play_state: "paused"`

#### Scenario: Transition in progress

- **WHEN** a caller probes `/health` after entering play mode was requested but before it completed
- **THEN** the response reports `play_state: "entering"`
