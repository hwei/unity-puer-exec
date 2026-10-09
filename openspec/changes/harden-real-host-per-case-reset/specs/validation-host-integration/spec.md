# Spec Delta

## ADDED Requirements

### Requirement: Per-case reset restores the active scene and clears residual modals

The real-host per-case reset SHALL return the shared Editor to a scene state that does not
depend on the previous case, and SHALL clear a residual modal before the next case runs, so a
case observes only the state it staged.

#### Scenario: A scene-dependent case does not inherit the previous scene

- **WHEN** a case needs a specific scene state, for example to raise a save-scene dialog
- **THEN** the case stages that state itself, or the reset restores it
- **AND** a previous case's scene does not change which dialog the case observes

#### Scenario: A residual modal does not distort the next case

- **WHEN** a previous case leaves a modal dialog up
- **THEN** the next case's reset clears it before the case runs
- **AND** the case's dialog assertions observe only the dialogs it staged itself

### Requirement: Real-host probes tolerate the control endpoint's reload window

The real-host harness SHALL probe the control endpoint through a shared helper that tolerates
the endpoint dropping during a domain reload and rebinding, possibly on a different port. A
probe SHALL fail a case only when the endpoint does not return within a bounded window, or when
the case explicitly requires an endpoint that is live at that moment.

#### Scenario: A probe lands inside a domain reload

- **WHEN** a case probes health right after a compile or a play-mode exit with a deferred compile
- **AND** the control endpoint is down for the reload or rebinds to another port
- **THEN** the shared probe re-resolves the endpoint and waits the reload out within its bound
- **AND** the case does not fail on a transport error unrelated to the behavior under test

#### Scenario: The endpoint never returns

- **WHEN** the endpoint does not come back within the probe's bound
- **THEN** the case fails with a message that names the reload window
- **AND** the failure is not masked by an unbounded retry
