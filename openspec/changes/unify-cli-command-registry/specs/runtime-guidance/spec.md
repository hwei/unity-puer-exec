## MODIFIED Requirements

### Requirement: Guidance covers all commands and statuses via a static matrix

The CLI SHALL maintain a static guidance matrix keyed by `(command, status)` that determines which `next_steps` and `situation` content to include in each response. The matrix SHALL cover every command in the authoritative flat command tree defined by the formal CLI contract, and all documented response statuses for each. The coverage requirement SHALL be expressed against that command tree rather than against a fixed command count, so adding a command extends the obligation automatically instead of leaving a stale number behind.

#### Scenario: Every documented non-success status has a guidance matrix entry

- **WHEN** a command returns any documented non-success status from the formal CLI contract
- **THEN** the guidance matrix provides either `next_steps`, `situation`, or both for that command × status combination

#### Scenario: Coverage follows the command tree

- **WHEN** a command is present in the authoritative flat command tree
- **THEN** the guidance matrix contains entries for that command
- **AND** a command added to the tree without matrix entries is detected rather than silently returning responses with no guidance

#### Scenario: Guidance matrix does not depend on response payload content

- **WHEN** the CLI constructs `next_steps` for a response
- **THEN** the candidates are determined by the command name and status alone
- **AND** the CLI does not inspect script-authored `result` fields to filter or reorder candidates

## ADDED Requirements

### Requirement: Compile-message commands carry freshness guidance

Responses from `get-compile-errors` and `get-compile-warnings` SHALL carry guidance covering the freshness hazard these commands are exposed to: compile messages read before a triggered compilation has settled report the previous compilation's results. The guidance SHALL point at the edge-aware compile wait as the way to establish that the messages being read belong to the intended compilation.

#### Scenario: Compile-message response explains the staleness hazard

- **WHEN** `get-compile-errors` or `get-compile-warnings` returns a response carrying guidance
- **THEN** the guidance explains that messages read before a compile settles belong to the previous compilation
- **AND** the candidates include waiting for the compile cycle before reading

#### Scenario: Compile-message commands carry guidance for service-contact statuses

- **WHEN** `get-compile-errors` or `get-compile-warnings` returns a non-success status arising from contacting the control service
- **THEN** the response carries `next_steps`, `situation`, or both, on the same terms as other service-contacting commands
