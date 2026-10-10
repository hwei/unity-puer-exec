## ADDED Requirements

### Requirement: Wait-for-compile accepts a compile-generation baseline

`wait-for-compile` SHALL accept an optional compile-generation baseline so that a caller which holds a value recorded before a domain reload can pass it to the command.

#### Scenario: Caller supplies a pre-reload baseline

- **WHEN** a caller records the compile generation before requesting a transition that crosses a domain reload
- **THEN** the caller can supply that value as `wait-for-compile`'s baseline

### Requirement: Wait-for-compile settles an inferred cross-reload compile from an advanced baseline

When the Editor reports a compile generation strictly greater than the supplied baseline, `wait-for-compile` SHALL report `compile_settled` with `compile_observed: true` and SHALL name the generation-advance edge. It SHALL return this outcome even when it never observed `compiling` and the endpoint was already `ready` at its first poll.

#### Scenario: Deferred play-exit compile crosses a reload

- **WHEN** `wait-for-compile` is invoked with a baseline recorded before play exit
- **AND** the Editor reports a compile generation greater than that baseline after the endpoint returns
- **THEN** the command reports `compile_settled` with `compile_observed: true`
- **AND** the result names the generation-advance edge
- **AND** it does not report `no_compile_observed`

### Requirement: Wait-for-compile never infers a settle without an advanced baseline

`wait-for-compile` SHALL keep its existing outcomes when no baseline is supplied or the baseline has not advanced. A caller that starts after the reload without a baseline SHALL receive `no_compile_observed`, not `compile_settled`.

#### Scenario: No baseline is supplied after the reload

- **WHEN** `wait-for-compile` is invoked after a reload without a compile-generation baseline
- **AND** the Editor is `ready` with no compile in progress
- **THEN** the command keeps its existing `no_compile_observed` outcome

#### Scenario: Supplied baseline is already current

- **WHEN** `wait-for-compile` is invoked with a baseline equal to the current compile generation
- **AND** no compilation completes within the appear window
- **THEN** the command reports `no_compile_observed`
