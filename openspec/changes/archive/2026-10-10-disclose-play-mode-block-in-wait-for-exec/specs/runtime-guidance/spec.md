## ADDED Requirements

### Requirement: Warning guidance composes all applicable CLI-owned conditions

When a warning response also carries a `compile_blocked` object, the response SHALL carry
`situation` and `next_steps` covering both the warning's own condition and the play-mode
compile block, rather than selecting one. The play-mode exit steps SHALL be present together
with the warning's own follow-up. Composition SHALL key on the CLI-composed `compile_blocked`
object and SHALL NOT read any script-authored `result` field. The single `warning` code SHALL
be unchanged.

#### Scenario: Async warning collides with a play-mode block

- **WHEN** an `exec` response reports `status: "warning"` with `warning: "async_result_not_supported"`
- **AND** the response carries a `compile_blocked` object
- **THEN** its `situation` states both that the entry function returned a Promise and that the pending change will not compile until play mode exits
- **AND** its `next_steps` include a step that exits play mode, a step that confirms play mode was exited, and a follow-up that waits for the compile cycle
- **AND** its `next_steps` preserve the warning's own async follow-up (`wait-for-result-marker`)
- **AND** `warning` remains `async_result_not_supported`

#### Scenario: A warning without a block is unchanged

- **WHEN** a warning response carries no `compile_blocked` object
- **THEN** its `situation` and `next_steps` are the same as before this composition existed

#### Scenario: Composition only adds, never replaces

- **WHEN** a warning response carries a `compile_blocked` object
- **THEN** the guidance candidates for the warning's own condition are still present
- **AND** the play-mode exit candidates are added rather than substituted
