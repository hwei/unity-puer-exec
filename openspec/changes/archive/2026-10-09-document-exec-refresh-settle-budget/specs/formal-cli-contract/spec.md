## ADDED Requirements

### Requirement: Help states that an automatic refresh settles on its own budget

The formal CLI help surface SHALL state that the compile cycle an automatic refresh starts is settled on a compile-scale budget of its own, and that this settle is not bounded by `--wait-timeout-ms`. The statement SHALL appear wherever `exec` describes its wait or timeout behavior, not only in the automatic-refresh description, so a caller choosing a small request-wait budget does not infer that a refresh is abandoned at that value. The status surface SHALL not imply the opposite.

#### Scenario: Agent reads exec help and learns the settle is not the request-wait budget

- **WHEN** a caller reads `exec --help`
- **THEN** the help states that an automatic refresh settles its compile cycle on a compile-scale budget
- **AND** it states that `--wait-timeout-ms` does not bound that settle
- **AND** the statement appears in the wait or timeout guidance, not only in the automatic-refresh description

#### Scenario: Agent reads exec status help and is not misled

- **WHEN** a caller reads `exec --help-status`
- **THEN** nothing on that surface implies that `--wait-timeout-ms` bounds an automatic refresh's settle
- **AND** the surface stays consistent with the statement made by `exec --help`

#### Scenario: Agent reads wait-for-compile help and finds the same cycle described consistently

- **WHEN** a caller reads `wait-for-compile --help`
- **THEN** the `--settle-timeout-seconds` description and the `exec` statement describe the same compile cycle
- **AND** neither surface contradicts the other
