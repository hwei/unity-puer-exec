## 1. Rewrite the three records

- [ ] 1.1 Re-read each target `meta.yaml` and record its exact current `evidence` values in order, so the rewrite can be checked against them. Verify: all three sets are captured before any edit.
- [ ] 1.2 Rewrite `2026-04-01-remove-wait-until-ready-command` `evidence` from the block list `- tests`, `- manual-check` to `evidence: tests, manual-check`. Verify: values and order match step 1.1.
- [ ] 1.3 Rewrite `2026-10-13-make-base-url-exec-refresh-recoverable` `evidence` from `[tests, host-validation, cli-transcript]` to `evidence: tests, host-validation, cli-transcript`. Verify: values and order match step 1.1.
- [ ] 1.4 Rewrite `2026-10-13-reproduce-play-mode-transport-reset-flake` `evidence` from the block list `- tests`, `- cli-transcript`, `- host-validation` to `evidence: tests, cli-transcript, host-validation`. Verify: values and order match step 1.1.
- [ ] 1.5 Confirm `git diff` on the three files touches only the `evidence` field. Verify: no other line, key, or blank line changed in any of the three records.

## 2. Enforce the canonical form

- [ ] 2.1 Add an assertion to the real-archive guard in `tests/test_openspec_change_meta.py` that no `openspec/changes/archive/*/meta.yaml` uses list-form `evidence`. Verify: the assertion inspects raw text, since parsing accepts both forms.
- [ ] 2.2 Confirm the new assertion is meaningful by checking it fails when run against a temporary list-form record. Verify: it is not a vacuously-true assertion.
- [ ] 2.3 Confirm the guard's legacy tolerance is unchanged: `KNOWN_LEGACY_ARCHIVE_RECORDS` still lists only records that fail for missing required fields. Verify: the constant is not widened to admit the three rewritten records.
- [ ] 2.4 Confirm `tools/openspec_change_meta.py` still accepts list form. Verify: no parser support was removed; the list-form test still passes.

## 3. Verify

- [ ] 3.1 Run `python -m unittest tests.test_openspec_change_meta tests.test_openspec_backlog`. Verify: OK.
- [ ] 3.2 Run the full default suite from `openspec/specs/validation-host-integration/how-to-run.md`. Verify: OK.
- [ ] 3.3 Load all three rewritten records through `openspec_change_meta.load_meta` and confirm `evidence` equals the step 1.1 values. Verify: identical strings.
- [ ] 3.4 Confirm `openspec_backlog.py list` still runs and these records are not listed (they are archived). Verify: no crash and no archive entries in output.

## 4. Closeout

- [ ] 4.1 Confirm `git diff` shows exactly three archived `meta.yaml` files plus test and change-artifact files. Verify: no other record was touched.
- [ ] 4.2 Complete the apply closeout review and state whether any new follow-up work was identified.
- [ ] 4.3 Record whether `define-evidence-as-multi-valued` has landed; if it has not, note that the `AGENTS.md` rule and this normalization are now decoupled.