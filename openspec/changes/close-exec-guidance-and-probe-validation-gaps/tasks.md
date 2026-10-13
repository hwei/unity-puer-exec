## 1. Close the real-host refresh-trigger staging gap

- [ ] 1.1 List every call site of `_write_compile_triggering_probe` and record the extension each one passes. Verify: the inventory shows every call site already passes a watched extension, so the new validation breaks none of them.
- [ ] 1.2 Confirm the watched extension set against the durable help statement (`.cs`, `.asmdef`, `.asmref`, `.rsp`) and against the Editor's own change signal, so the new check does not introduce a second, drifting list. Verify: the finding cites the help text and the server-side detection, and names any extension one has and the other lacks.
- [ ] 1.3 Make `_write_compile_triggering_probe` reject a probe name outside the watched set before writing anything, naming the watched extensions. Verify: a mistyped probe fails with no Editor launch and no validation-host write.
- [ ] 1.4 Improve the `_wait_for_refresh_pending` failure message to name the watched extensions and the observed `skipped_reason`, keeping the existing distinct message for an endpoint that never returned at all. Verify: a correctly staged but unobserved probe names the cause, and the endpoint-timeout path still reports a dropped control endpoint rather than a change-signal problem.
- [ ] 1.5 Add regression coverage for the staging rejection and for the wait failure message. Verify: each fails without 1.3 or 1.4 respectively, and neither requires a live Editor.

## 2. Restore the continuation for an accepted base-url request

- [ ] 2.1 Confirm against the CLI (mocked transport) that `exec --base-url` returning `running` for an accepted request currently advertises no `wait-for-exec` candidate, while the addressed service would answer `wait-for-exec --base-url --request-id` for that same `request_id`. Verify: the finding is reproduced, not inferred, and names the response status that proves the request was accepted.
- [ ] 2.2 Add a `--base-url` `argv_template` variant to the `("exec", "running")` `wait-for-exec` candidate and select on the selector. Verify: an accepted base-url `running` response carries a candidate with a complete `--base-url` argv, and the project-path candidate is unchanged.
- [ ] 2.3 Re-express `requires_replayable_record` as record presence rather than template fillability, per design Decision 3, and confirm a `refresh_unsettled` response still offers no such candidate. Verify: both directions are asserted on the caller-visible response.
- [ ] 2.4 Pin that the two template variants differ only in the selector and render the same `when`. Verify: the assertion fails if either variant's `when` drifts.
- [ ] 2.5 Re-run the exec lifecycle and guidance suites and confirm no pre-existing guidance guarantee was relaxed. Verify: green, with each changed assertion reviewed rather than deleted.

## 3. Validation and Closeout

- [ ] 3.1 Run the focused Python suites (`tests.test_unity_session_cli`, `tests.test_unity_session_modules`, `tests.test_openspec_spec_hygiene`) and confirm `missing` still reports non-recoverably for genuinely absent records. Verify: green.
- [ ] 3.2 Run the real-host suite against the validation host and confirm the refresh cases still cross real reloads with the new probe validation in place. Verify: the refresh cases pass, and a probe written through the helper is rejected locally when its extension is wrong.
- [ ] 3.3 Run `openspec validate close-exec-guidance-and-probe-validation-gaps --strict` and `openspec validate --all`, confirming the two reconciled requirements no longer read as contradictions. Verify: the delta matches the implemented behavior.
- [ ] 3.4 Complete the required apply closeout review and record the finding with allowed categories, separating these gaps from the intermittent launch-recovery and CLI empty-response flakes. Verify: the closeout names each candidate and its disposition.