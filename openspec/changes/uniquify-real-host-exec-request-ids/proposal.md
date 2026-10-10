# Proposal

## Why

`harden-real-host-per-case-reset` repeated `test_resolve_blocker_cancel_is_rejected_for_save_scene_against_real_host` in one process. The second and third runs did not stage a dialog: the exec `request_id` was `os.getpid()`, and the server treats a repeated id with the same code as the already completed request. That one call site now uses `time.time_ns()`. Eight other real-host exec ids in the same module still use only the process id.

## What Changes

- Give every real-host exec `request_id` in `tests/test_real_host_integration.py` a value that changes on each invocation inside one process.
- Cover that rule with a unit test so a same-process repeat does not depend on another Editor launch.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `validation-host-integration`: a real-host exec request id is unique per invocation, not derived only from the process id.

## Impact

- `tests/test_real_host_integration.py`
- `tests/test_real_host_reset.py` or the existing unit module that locks harness source
- No product CLI or server change. The server's same-id replay behavior stays.
