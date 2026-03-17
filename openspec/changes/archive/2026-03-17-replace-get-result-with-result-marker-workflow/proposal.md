# Proposal

## Summary

Replace the continuation-token async workflow with the accepted result-marker workflow. Remove `get-result` from the formal CLI and package surface, and make long-running observation rely on `exec`, `wait-for-log-pattern`, and `wait-for-result-marker`.

## Why

The repository has already converged on a simpler async model:

- scripts emit single-line JSON result markers with `correlation_id`
- `wait-for-log-pattern` remains the low-level regex primitive
- `wait-for-result-marker` becomes the recommended high-level workflow
- `exec --include-log-offset` provides the observation checkpoint needed to wait safely

Keeping `get-result` as a compatibility layer would preserve two async models at once:

- continuation-token polling
- log-driven observation

That would increase implementation, help-surface, and test complexity without protecting a real installed user base. The product is still unstable and not yet adopted, so it is cheaper to move directly to the final workflow now.

## Proposed Change

- remove `get-result` from the CLI command tree
- remove the package-side `/get-result` endpoint and continuation-based job lookup path
- add `wait-for-result-marker`
- extend `wait-for-log-pattern` with extraction modes:
  - `--extract-group`
  - `--extract-json-group`
- extend `exec` with `--include-log-offset`
- update help, examples, and tests to use the result-marker workflow as the only formal long-running path

## Expected Outcome

The CLI exposes one async workflow:

1. `exec --include-log-offset`
2. script returns `correlation_id`
3. script later emits a single-line JSON result marker
4. caller waits with `wait-for-result-marker --correlation-id ... --start-offset ...`

The package no longer needs to implement dedicated continuation-token result polling.
