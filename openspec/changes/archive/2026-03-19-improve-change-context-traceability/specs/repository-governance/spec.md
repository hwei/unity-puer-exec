## ADDED Requirements

### Requirement: Follow-up changes preserve prerequisite evidence context
When a change depends on prior validation, retrospective findings, or archived change conclusions to make its scope understandable, the change SHALL identify the upstream change names and summarize the inherited findings in its proposal or design artifacts. Contributors MUST NOT rely on unstated team memory or metadata-only dependency references as the sole way to reconstruct that context.

#### Scenario: Follow-up optimization change builds on prior validation
- **WHEN** a contributor proposes a follow-up change whose rationale depends on what an earlier validation change already proved
- **THEN** the proposal or design names the upstream validation change
- **AND** the current change summarizes the finding that remains true and the gap that still needs work
- **AND** a fresh reader can understand why the new change exists without separately guessing the evidence chain from oral background alone

#### Scenario: Current change references archived findings
- **WHEN** a non-archived change depends on findings that live in archived change artifacts
- **THEN** the current change cites the archived change by name
- **AND** the current change explains which archived finding is being carried forward into current scope
- **AND** the reader does not need to inspect backlog metadata alone to infer the narrative dependency
