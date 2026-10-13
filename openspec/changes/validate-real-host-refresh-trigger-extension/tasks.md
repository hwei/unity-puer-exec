## 1. Confirm the gap and the watched set

- [ ] 1.1 List every call site of `_write_compile_triggering_probe` and record the name each one passes. Verify: the inventory shows every call site already stages a watched extension, so the new validation breaks none of them.
- [ ] 1.2 Read the durable help statement about which changes trigger automatic refresh and record the extensions it names. Verify: the finding cites the help text rather than restating it from memory.
- [ ] 1.3 Confirm against the Editor-side change signal that the watched set is exactly those extensions, and record any extension one has and the other lacks. Verify: the finding names both sources and resolves the difference.
- [ ] 1.4 Reproduce the failure locally: stage a probe without a watched extension and confirm the Editor reports `no_pending_change` rather than a refresh. Verify: reproduced against the host, so the fix targets the observed condition.

## 2. Validate the probe and sharpen the wait message

- [ ] 2.1 Make `_write_compile_triggering_probe` reject a probe name outside the watched set before writing anything, naming the watched extensions. Verify: a mistyped probe fails with no Editor launch and no validation-host write.
- [ ] 2.2 Source the watched set from the durable help statement rather than an inline literal, so the two cannot drift. Verify: a change to the help entry surfaces at staging time rather than silently accepting a name the Editor ignores.
- [ ] 2.3 Make the `_wait_for_refresh_pending` failure name the watched extensions and the observed `skipped_reason`, keeping the existing distinct message for a control endpoint that never returned. Verify: a correctly staged but unobserved probe names the cause, and the endpoint-timeout path still reports a dropped endpoint.
- [ ] 2.4 Add regression coverage for the staging rejection and the wait failure message. Verify: each fails without 2.1 or 2.3 respectively, and neither requires a live Editor for the staging rejection.

## 3. Validation and Closeout

- [ ] 3.1 Run the real-host suite against the validation host and confirm the refresh cases still cross real reloads with the new validation in place. Verify: the refresh cases pass, and a probe written through the helper is rejected locally when its extension is wrong.
- [ ] 3.2 Confirm no product code changed and no product output is affected. Verify: `git diff` touches only `tests/test_real_host_integration.py` and this change's artifacts.
- [ ] 3.3 Run `openspec validate validate-real-host-refresh-trigger-extension --strict` and `openspec validate --all`. Verify: the delta matches the implemented behavior.
- [ ] 3.4 Complete the required apply closeout review and record the finding with allowed categories, separating this staging gap from the guidance gap in `restore-base-url-exec-continuation-guidance` and from the intermittent launch-recovery and CLI empty-response flakes. Verify: the closeout names each candidate and its disposition.