## Why

The archived spike `improve-openspec-change-status-querying` concluded that repository backlog state and OpenSpec workflow state answer different questions, but the follow-up discussion exposed a deeper possibility: the repository may be carrying too much manually maintained planning state in `meta.yaml.status` in the first place. If backlog recommendation can be derived more directly from repository facts such as unresolved dependencies, archive state, and recent change activity, the workflow may become more trustworthy by reducing state drift instead of merely explaining it.

## What Changes

- Explore whether repository backlog recommendation should be derived primarily from repository facts rather than hand-maintained status transitions.
- Define which planning signals should remain explicit manual metadata and which should become derived eligibility or ranking inputs.
- Compare candidate activity signals, including Git commit distance versus wall-clock recency, for recommending whether a recently touched change should be continued.
- Clarify how superseded or replaced changes should still follow the standard OpenSpec disposition path rather than being silently deleted.
- Converge on a model where `superseded` is at most a short-lived pre-archive disposition and `queued` / `active` / `blocked` no longer drive backlog recommendation directly.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `change-backlog-triage`: backlog recommendation rules may shift from explicit queued/active/blocked state management toward repository-derived eligibility and ranking, while narrowing superseded to a temporary archive-bound disposition.

## Impact

- Affects repository workflow semantics in `openspec/specs/change-backlog-triage/spec.md`.
- Likely affects `tools/openspec_backlog.py` and any repository guidance that currently treats `meta.yaml.status` as the primary backlog driver.
- Affects how maintainers and agents interpret `blocked_by`, archived prerequisites, superseded changes, and recent Git activity when deciding what to work on next.
