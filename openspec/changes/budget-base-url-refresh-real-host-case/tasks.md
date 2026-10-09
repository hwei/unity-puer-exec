## 1. Budget the case at the compile scale

- [ ] 1.1 Give the refresh-triggering first `exec` in `test_base_url_automatic_refresh_and_wait_for_compile_against_real_host` a compile-scale wait budget, matching the sibling refresh classes. Verify: the request is bounded by the refresh-scale constant, not `WAIT_TIMEOUT_MS = 1000`.
- [ ] 1.2 Assert the refresh disclosure on the terminal `exec` response and stop treating a `wait-for-exec` payload as that evidence. Verify: the case fails, rather than passing, when the payload it checks is a `wait-for-exec` continuation.

## 2. Validation

- [ ] 2.1 Run the case against the real host with a compilable package. Verify: green, and the terminal payload carries `refresh.triggered=true` with reason `compile_triggering_change`.
- [ ] 2.2 Run the default unit suite and `openspec validate budget-base-url-refresh-real-host-case`. Verify: both green.
