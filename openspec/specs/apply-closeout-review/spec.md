# Apply Closeout Review

## Purpose

Define the repository's required apply-closeout review, follow-up candidate reporting, and end-of-change action recommendations.

## Requirements

### Requirement: Apply closeout reports whether new follow-up work was found

Every apply session SHALL end with an explicit closeout finding summary stating either that no new follow-up work was identified or that new follow-up candidates were identified.

#### Scenario: Apply session completes without new follow-up work

- **WHEN** an apply session completes and no new follow-up candidates were discovered
- **THEN** the closeout explicitly states that no new follow-up work was identified
- **AND** the result is distinguishable from a closeout that omitted review

### Requirement: New follow-up candidates are classified consistently

When apply closeout identifies new follow-up candidates, the closeout SHALL classify each candidate using one of the repository categories `product-improvement`, `workflow-improvement`, `tooling-improvement`, or `validation-gap`.

#### Scenario: Apply session discovers workflow and tooling follow-ups

- **WHEN** an apply session identifies new workflow or tooling follow-up candidates
- **THEN** the closeout lists each candidate with one of the allowed follow-up categories
- **AND** the closeout provides enough context for a human to discuss disposition

### Requirement: New follow-up candidates require human discussion before promotion

When apply closeout identifies new follow-up candidates, the agent SHALL surface them for human discussion before promoting them into new queued changes, implementation work, or other persistent follow-up actions.

#### Scenario: Agent identifies a product-improvement candidate during closeout

- **WHEN** the closeout includes a newly identified product-improvement candidate
- **THEN** the agent asks the human how to dispose of the candidate
- **AND** the agent does not silently create or continue additional work as if the candidate were already accepted

### Requirement: Apply closeout recommends repository actions when ready

Apply closeout SHALL evaluate whether the current change is ready for `git commit`, `openspec archive`, and a final `git commit`, and SHALL recommend the sequence when the state is appropriate.

#### Scenario: Change is complete and ready to close

- **WHEN** apply work completes and the repository state is ready for closeout
- **THEN** the closeout recommends whether to create a checkpoint commit
- **AND** the closeout recommends whether to archive the change
- **AND** the closeout recommends whether to create the final post-archive commit
