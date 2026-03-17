## Why

The repository now has stronger OpenSpec apply and backlog rules, but apply closeout still relies on ad hoc judgment. We need explicit closeout behavior so agents report newly discovered follow-up work, discuss it with the human before continuing, and recommend the appropriate commit/archive sequence when a change is ready to close.

## What Changes

- Add durable closeout requirements for reporting newly discovered follow-up candidates at the end of apply work.
- Define follow-up candidate categories so product and workflow improvements are surfaced consistently.
- Require apply closeout to recommend whether the current state is ready for a `git commit`, `openspec archive`, and final `git commit`.
- Update repository guidance so agents treat closeout review as part of apply completion rather than an optional courtesy.

## Capabilities

### New Capabilities
- `apply-closeout-review`: Defines the required apply-closeout report for follow-up candidates and end-of-change action recommendations.

### Modified Capabilities
- `repository-governance`: Extend repository workflow rules to require human discussion before newly discovered follow-up candidates are promoted into further work.

## Impact

- Adds a new durable workflow capability under `openspec/specs/`.
- Updates repository governance and agent guidance for apply-closeout behavior.
- Shapes future apply sessions by standardizing follow-up review and commit/archive recommendations.
