# Spec Delta

## ADDED Requirements

### Requirement: Proposal runtime claims state their basis

When a proposal's rationale rests on a concrete runtime behavior (for example a call count, a
resolution pass, or a probe count), the proposal SHALL state whether that claim is measured or an
unverified hypothesis, and SHALL name the measurement when one exists. A claim that rests on
human observation which cannot be collected automatically MAY be disclosed as an unverified
hypothesis instead, with the apply tasks verifying it before implementation relies on it.

#### Scenario: Rationale rests on a measured runtime behavior

- **WHEN** a proposal justifies itself with a concrete runtime behavior that was measured
- **THEN** the proposal states that the claim is measured
- **AND** the proposal names the measurement so a reader can reproduce it

#### Scenario: Rationale rests on an uncollected observation

- **WHEN** a proposal justifies itself with a concrete runtime behavior that was only observed by
  hand and not collected automatically
- **THEN** the proposal discloses the claim as an unverified hypothesis rather than as measured
- **AND** the apply tasks include a step that verifies the hypothesis before implementation relies
  on it
