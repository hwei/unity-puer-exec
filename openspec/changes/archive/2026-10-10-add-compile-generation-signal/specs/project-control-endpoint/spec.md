## ADDED Requirements

### Requirement: Health response exposes a monotonic compile generation

The ready `/health` response SHALL include a compile generation that increases by at least one each time a script compilation completes and never decreases. The generation SHALL be persisted so that it survives a domain reload and resumes from its prior value in the new domain rather than resetting to an initial value.

#### Scenario: Ready response reports the generation

- **WHEN** a caller probes `/health` on a ready service
- **THEN** the response includes the compile generation

#### Scenario: A completed compilation advances the generation

- **WHEN** a script compilation completes
- **THEN** the compile generation increases
- **AND** the increase is observable on `/health` once the Editor is ready again

#### Scenario: Generation survives a domain reload

- **WHEN** the Editor reloads its domain after a compilation
- **THEN** the compile generation reported after the reload is greater than the value reported before it
- **AND** it is not reset to a cold-start value
