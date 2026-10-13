## 1. Confirm the remaining gap

- [ ] 1.1 Enumerate every `GUIDANCE_MATRIX` candidate whose `argv_template` names `--project-path`, and mark which target commands accept `--base-url`. Verify: the list names each candidate, its status key, and whether it is convertible.
- [ ] 1.2 Reproduce the gap for `wait-for-exec --base-url` returning `running` and `exec --base-url` returning `completed` (mocked transport). Verify: reproduced on the caller-visible response, not inferred.

## 2. Convert the convertible candidates

- [ ] 2.1 Add a `--base-url` `argv_templates` variant to the `("wait-for-exec", "running")` candidate. Verify: a base-url running response carries a `--base-url` argv, and the project-path argv is unchanged.
- [ ] 2.2 Do the same for the shared `get-log-briefs` completed candidate (`exec`, `wait-for-exec`, `wait-for-log-pattern`). Verify: a base-url completed response carries `--base-url` plus `--range` and `--levels`.
- [ ] 2.3 Convert any further candidate the 1.1 inventory marks convertible, and leave the rest unchanged. Verify: no candidate gains a selector flag its command does not accept.

## 3. Validation and Closeout

- [ ] 3.1 Add regression coverage for each converted candidate under both selectors. Verify: base-url assertions fail without 2.1/2.2, and project-path assertions pin the unchanged form.
- [ ] 3.2 Run `tests.test_unity_session_cli`, `tests.test_unity_session_modules`, and `tests.test_openspec_spec_hygiene`. Verify: green, no pre-existing guidance guarantee relaxed.
- [ ] 3.3 Run `openspec validate restore-base-url-argv-for-remaining-continuations --strict` and `openspec validate --all`. Verify: the delta matches the implemented behavior.
- [ ] 3.4 Complete the required apply closeout review and record the finding with allowed categories, separating it from the guidance-record rule and the harness follow-ups.
