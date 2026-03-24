## MODIFIED Requirements

### Requirement: New follow-up candidates require human discussion before promotion

When apply closeout identifies new follow-up candidates, the agent SHALL surface them for human discussion before promoting them into new follow-up changes, implementation work, or other persistent follow-up actions.

#### Scenario: Agent identifies a product-improvement candidate during closeout

- **WHEN** the closeout includes a newly identified product-improvement candidate
- **THEN** the agent asks the human how to dispose of the candidate
- **AND** the agent does not silently create or continue additional work as if the candidate were already accepted
