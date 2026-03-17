## ADDED Requirements

### Requirement: Apply closeout findings remain review inputs until disposition

New follow-up candidates discovered during apply closeout SHALL remain explicit review inputs until the human accepts, defers, rejects, or converts them into follow-up work. Agents MUST NOT silently promote apply-closeout findings into repository workflow without human discussion.

#### Scenario: Apply closeout identifies a workflow-improvement candidate

- **WHEN** an apply closeout reports a new workflow-improvement candidate
- **THEN** the candidate is surfaced as an explicit discussion item
- **AND** the agent waits for human disposition before promoting it into a queued change or further implementation
