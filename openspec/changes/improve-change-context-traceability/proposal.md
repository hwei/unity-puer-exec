## Why

The repository is now creating follow-up changes from prior validation work, but the new change documents do not always let a fresh reader reconstruct the evidence chain without outside memory. This became visible in `improve-cli-help-for-agent-efficiency`, which assumes readers know that help-only subagent validation already succeeded, that the remaining problem was efficiency, and that a later change added transcript capture specifically so the next help iteration could be evidence-driven.

## What Changes

- Require proposal and design artifacts for follow-up changes to cite the concrete upstream changes and findings they build on when those findings are necessary to understand scope.
- Clarify that `meta.yaml` dependency fields remain machine-readable planning metadata, not a substitute for human-readable background and evidence summaries.
- Add durable governance rules for change traceability so a contributor can reconstruct prerequisite context from the current change artifacts rather than relying on oral project memory.
- Tighten expectations around active-versus-archived change visibility so stale or duplicate change entries do not obscure the intended evidence trail.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `repository-governance`: follow-up changes should summarize the upstream evidence chain and explain why the cited predecessor matters.
- `change-backlog-triage`: change metadata should remain limited to machine-readable planning state and should not be treated as sufficient narrative context for dependent work.

## Impact

- Affects how OpenSpec proposals and designs are authored and reviewed in this repository.
- Affects governance requirements for linking validation changes, evidence artifacts, and follow-up optimization changes.
- May affect helper tooling or review checklists if the repository later automates traceability checks.
