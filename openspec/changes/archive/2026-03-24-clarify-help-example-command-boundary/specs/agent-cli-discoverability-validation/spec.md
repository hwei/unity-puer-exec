## ADDED Requirements

### Requirement: Top-level help distinguishes workflow examples from executable commands
The CLI SHALL label workflow-style help entries in a way that makes clear they are `--help-example` targets rather than executable subcommands.

#### Scenario: Contributor discovers a workflow example from top-level help
- **WHEN** a contributor reads top-level help and sees a workflow such as `exec-and-wait-for-log-pattern`
- **THEN** the help text indicates that the workflow is an example identifier for `--help-example`
- **AND** the wording does not present that identifier as if it were a direct subcommand
- **AND** Prompt B validation can compare whether agents still make a first-pass subcommand mistake after the help change
