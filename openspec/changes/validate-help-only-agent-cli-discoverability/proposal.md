## Why

The repository now exposes a deliberate CLI help surface, but it is still unclear whether that published surface is enough for an agent to discover and operate the real Unity Editor workflow without reading repository-only source or tests. We need a repeatable validation protocol that measures real help-driven usability before investing in more automation or more help text.

## What Changes

- Define a repository-owned validation protocol for help-only agent trials against the real Unity Editor workflow.
- Establish experiment boundaries that allow only the published CLI help surface plus normal CLI execution, while disallowing repository-only source and tests.
- Define a small first-round task set that measures both simple execution and longer multi-step workflows.
- Define a scoring and findings format that separates task success, autonomy, and efficiency so discoverability gaps can be traced back to the CLI surface.

## Capabilities

### New Capabilities
- `agent-cli-discoverability-validation`: Defines the durable validation protocol for measuring whether agents can discover and operate the published CLI help surface in real Unity Editor tasks.

### Modified Capabilities
- None.

## Impact

- Affects OpenSpec validation artifacts and repository-owned validation workflow expectations.
- Shapes how future CLI discoverability regressions are evaluated before more help or harness work is added.
- May later drive follow-up work in help text, validation tooling, or harness automation, but does not itself change the formal CLI behavior.
