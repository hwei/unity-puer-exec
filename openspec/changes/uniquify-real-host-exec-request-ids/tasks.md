## 1. Unique request ids

- [x] 1.1 Add `_unique_request_id(prefix)` and use it for every exec `request_id` in `tests/test_real_host_integration.py`, including the save-scene cancel id that already calls `time.time_ns()`. Verify: the module no longer formats an exec request id from `os.getpid()` alone, and two helper calls in one process differ.
- [x] 1.2 Lock that rule in the unit suite. Verify: a test fails if an exec `--request-id` or `request_id` assignment in the module is built only from `os.getpid()`.

## 2. Validation

- [x] 2.1 Run the default unit suite and `openspec validate uniquify-real-host-exec-request-ids`. Verify: both green.
