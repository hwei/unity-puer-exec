## Why

The sequential validation for `improve-cli-help-for-agent-efficiency` improved command discoverability, but it also exposed a deeper product gap that help text alone cannot close. When `exec` returns `not_available` or times out at the transport layer, the current CLI does not let the caller distinguish between "the request was never accepted" and "the request may have been accepted but the client lost the response."

That ambiguity matters for real Unity work because retrying a side-effecting script can duplicate file writes, scene edits, menu registration, or other editor actions. The current workflow partially solves long-running observation with script-provided `correlation_id` plus `log_offset`, but that is not the same as a repository-owned execution identity and it does not cover the transport-timeout ambiguity directly.

This follow-up change exists to define a recoverable execution contract for `exec`, then publish that contract through help that agents and humans can actually follow.

## What Changes

- Define a formal contract for how `exec` identifies a submitted request and how callers can reason about timeout or unavailable responses.
- Add a public observation or recovery path that lets callers determine whether an `exec` request was accepted, still running, completed, or never observed by the service.
- Update the published help and examples so the timeout-recovery workflow is understandable without repository-only hints.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `formal-cli-contract`: `exec` should expose a recoverable request identity and timeout-recovery guidance.
- `agent-cli-discoverability-validation`: validation should be able to evaluate the timeout-recovery workflow through the published help surface.

## Impact

- Affects `unity-puer-exec` request identity, timeout semantics, and observation workflow.
- Affects the public help surface and examples for `exec`.
- Depends on finishing `improve-cli-help-for-agent-efficiency` first so help-only command hierarchy work is not mixed with deeper execution-contract changes.
