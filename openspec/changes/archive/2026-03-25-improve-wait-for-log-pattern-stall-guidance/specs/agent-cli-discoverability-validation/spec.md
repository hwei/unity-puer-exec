## ADDED Requirements

### Requirement: Wait-for-log-pattern stalled outcomes preserve a publishable recovery path
The repository SHALL allow log-oriented validation to evaluate whether a `wait-for-log-pattern` result of `unity_stalled` still leaves contributors with a clear published recovery path that favors continued CLI-native verification over direct host-log fallback.

#### Scenario: Contributor hits unity_stalled during log verification
- **WHEN** a contributor or help-only validating agent gets `unity_stalled` from `wait-for-log-pattern`
- **THEN** the published CLI surface identifies a reasonable next recovery step or adjustment that can be attempted without repository-only guidance
- **AND** later validation can record whether the workflow stayed inside the CLI observation surface or still fell back to direct host-log inspection
