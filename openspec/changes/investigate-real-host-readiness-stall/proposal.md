## Why

Follow-up validation after `add-exec-script-args` showed that the real-host suite is not currently a stable archive gate. Sequential runs can enter `wait-until-ready -> unity_stalled` after teardown, and some real-host assertions no longer match the current CLI surface.

## What Changes

- Investigate and narrow the real-host readiness stall so the repository can distinguish harness sequencing failures from true product regressions.
- Stabilize the repository-owned real-host test boundary between teardown and the next readiness attempt.
- Refresh real-host validation expectations that still target removed or renamed CLI response fields.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `validation-host-integration`: the real-host workflow must provide a repeatable sequential test boundary and must track the current observation-checkpoint surface used by project-scoped `exec`.

## Impact

- `tests/test_real_host_integration.py` and its helper flow
- Project-scoped readiness and stop orchestration in `cli/python/unity_session.py` and related runtime helpers
- Validation documentation and OpenSpec truth for real-host regression coverage
