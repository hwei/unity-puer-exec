## 1. Confirm the gap and the record-presence rule

- [ ] 1.1 Confirm against the CLI (mocked transport) that `exec --base-url` returning `running` for an accepted request currently advertises no `wait-for-exec` candidate. Verify: reproduced, not inferred, and the response status recorded as the evidence that the request was accepted.
- [ ] 1.2 Confirm the addressed service *would* answer `wait-for-exec --base-url --request-id` for that same `request_id`, so restoring the candidate does not reproduce the `missing` defect the rule exists to prevent. Verify: shown with a mocked transport that returns the accepted job's terminal response.
- [ ] 1.3 Enumerate every status that carries the `("exec", "running")` `wait-for-exec` candidate, and confirm which of them the service holds a record for. Verify: the list separates statuses where presence follows the record from statuses where it must not, and covers `busy`.

## 2. Restore the continuation and keep the rule honest

- [ ] 2.1 Add a `--base-url` `argv_template` variant to the `("exec", "running")` `wait-for-exec` candidate and select between the two on the selector. Verify: an accepted base-url `running` response carries a candidate with a complete `--base-url` argv, and the project-path candidate is byte-identical to today's.
- [ ] 2.2 Re-express `requires_replayable_record` as record presence rather than template fillability, per design Decision 2, reading the answer from the CLI-composed payload rather than the selector. Verify: the source of the answer is the payload, and no extra transport call is introduced.
- [ ] 2.3 Confirm a `refresh_unsettled` response still offers no `wait-for-exec` candidate, and that `busy` is unaffected. Verify: asserted on the caller-visible response, so the fix cannot be made by removing the rule.
- [ ] 2.4 Pin that the two template variants differ only in the selector and render the same `when`. Verify: the assertion fails if either variant's `when` drifts.
- [ ] 2.5 Add regression coverage for a base-url `running` response, a project-path `running` response, and a `refresh_unsettled` response. Verify: each fails without 2.1 or 2.2.

## 3. Validation and Closeout

- [ ] 3.1 Run the exec lifecycle and guidance suites (`tests.test_unity_session_cli`, `tests.test_unity_session_modules`, `tests.test_openspec_spec_hygiene`) and confirm no pre-existing guidance guarantee was relaxed. Verify: green, with each changed assertion reviewed rather than deleted.
- [ ] 3.2 Confirm `missing` still reports non-recoverably for genuinely absent records, and that no guidance text claims a continuation the CLI cannot honor. Verify: the exec lifecycle coverage for absent and expired records is unchanged.
- [ ] 3.3 Run `openspec validate restore-base-url-exec-continuation-guidance --strict` and confirm the two reconciled requirements no longer read as contradictions. Verify: the delta matches the implemented behavior.
- [ ] 3.4 Complete the required apply closeout review and record the finding with allowed categories, separating this guidance gap from the real-host staging gap in `validate-real-host-refresh-trigger-extension` and from the intermittent launch-recovery and CLI empty-response flakes. Verify: the closeout names each candidate and its disposition.