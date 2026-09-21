## ADDED Requirements

### Requirement: Real-host suite cost scales with cases, not with host relaunches

The repository-owned real-host validation workflow SHALL bring the validation host
Editor up at most once per suite run and SHALL reuse that Editor across its cases, so
adding a case does not add a full Editor launch. Per-case isolation SHALL be achieved
by resetting test-owned state between cases — repository-owned validation temp assets,
Editor play mode, and any test-owned session or change-signal state — rather than by
stopping and relaunching the Editor. A case that genuinely requires a pristine process
(for example batch-mode activation behavior or preferred-port rollover) SHALL be able to
opt into its own launch boundary, and SHALL say so rather than silently bypass the
shared host.

#### Scenario: Sequential cases reuse one Editor

- **WHEN** a contributor runs the real-host suite and the first case has brought the
  host up
- **THEN** subsequent cases in the same suite run reuse that Editor
- **AND** the suite does not stop and relaunch the Editor between ordinary cases

#### Scenario: A case does not observe another case's leftovers

- **WHEN** one case leaves repository-owned validation temp assets, a pending refresh
  signal, or an Editor in play mode
- **THEN** the next case starts from a reset state
- **AND** its assertions are not affected by the previous case's leftovers

#### Scenario: A pristine-process case keeps its own boundary

- **WHEN** a case requires a process that the shared Editor cannot provide, such as a
  batch-mode launch or a specific occupied-port condition
- **THEN** that case opts into its own launch and stop boundary
- **AND** it reports its boundary result rather than assuming the shared host

#### Scenario: A host that dies mid-suite is handled explicitly

- **WHEN** the shared Editor exits or stops responding while the suite is running
- **THEN** the workflow either re-establishes the host within its bounded retry budget
  or fails the case with machine-usable launch diagnostics
- **AND** it does not report a pass against a host that was not running

#### Scenario: The suite still establishes its starting boundary

- **WHEN** the suite begins
- **THEN** it establishes the clean starting boundary from project-local state before
  bringing the host up
- **AND** the boundary rules for lockfile and published endpoint are unchanged from the
  per-case model
