# Design

## Problem

The current implementation records `log_offset` inside the Unity package by calling `ReadEditorLogOffset()` in `UnityPuerExecServer.cs`, while CLI observers read the Editor log through the observation logic in `cli/python/unity_session.py`.

Real-host validation showed that these two sides are not aligned:

- `exec --include-log-offset` returned `log_offset = 0`
- `wait-for-result-marker` still succeeded because it could scan the full log and find the marker later
- `wait-for-log-pattern --extract-json-group` did not get a trustworthy observation start point from that `log_offset`

So the product currently satisfies only the broad "result marker can be found" path, but not the intended precise observation contract.

## Design Direction

The contract should treat `log_offset` as an observation checkpoint that is valid for the same log source used by `wait-for-log-pattern` and `wait-for-result-marker`.

This change should:

- identify the authoritative log source for host observation
- make `exec --include-log-offset` return an offset taken against that same source
- preserve the current top-level placement and opt-in behavior of `log_offset`
- prove the corrected behavior through real Unity host validation

## Validation Targets

After the fix lands, real-host validation should prove at least these cases:

1. `exec --include-log-offset` returns a non-stale offset compatible with later observation.
2. `wait-for-result-marker --correlation-id ... --start-offset ...` succeeds from the returned offset.
3. `wait-for-log-pattern --extract-json-group ... --start-offset ...` can also observe the same marker from the returned offset.
4. Optional `--expected-session-marker` still works on the corrected path.

## Out of Scope

- changing the result-marker format
- changing diagnostics visibility policy
- reintroducing `get-result`
