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
