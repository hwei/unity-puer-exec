## 1. Establish the baseline

- [ ] 1.1 Re-run the measurement in design.md (archive directory count, records with no `meta.yaml`, records with a partial `meta.yaml`, records with list-form `evidence`) and confirm the target sets still match: 10 with no file, 4 partial, 3 list-form. Verify: the numbers are current, not copied from the proposal; any newly archived record that falls into a gap is added to scope.
- [ ] 1.2 Record the exact current `evidence` values, in order, of the three list-form records. Verify: all three sets are captured before any edit.
- [ ] 1.3 Record the output of `python tools/openspec_backlog.py list` for later comparison. Verify: saved under `.tmp/`.

## 2. Rewrite the three list-form records

- [ ] 2.1 Rewrite `2026-04-01-remove-wait-until-ready-command` `evidence` to `evidence: tests, manual-check`. Verify: values and order match step 1.2.
- [ ] 2.2 Rewrite `2026-10-13-make-base-url-exec-refresh-recoverable` `evidence` to `evidence: tests, host-validation, cli-transcript`. Verify: values and order match step 1.2.
- [ ] 2.3 Rewrite `2026-10-13-reproduce-play-mode-transport-reset-flake` `evidence` to `evidence: tests, cli-transcript, host-validation`. Verify: values and order match step 1.2.
- [ ] 2.4 Confirm `git diff` on the three files touches only the `evidence` field, and each loads through `openspec_change_meta.load_meta` with `evidence` equal to the step 1.2 join. Verify: no other line, key, or blank line changed.

## 3. Gather evidence for the 14 backfill targets

- [ ] 3.1 For each of the 14 target records, gather its own evidence: `proposal.md`, `tasks.md` completion state, and last real commit date. Verify: every record has all three before any field is written.
- [ ] 3.2 Record the inferred value and its justification for each of the 14 in the backfill justification table in design.md, as each is decided. Verify: no row says only "inferred".

## 4. Backfill the 10 missing files

- [ ] 4.1 Write `meta.yaml` for `2026-03-17-add-apply-closeout-governance`, with `change_type`, `priority`, `blocked_by`, `assumption_state`, scalar `evidence`, and `updated_at` justified by its proposal. Verify: it parses via `openspec_change_meta.load_meta`.
- [ ] 4.2 Same for `2026-03-17-archive-legacy-decisions`. Verify: parses.
- [ ] 4.3 Same for `2026-03-17-delete-legacy-docs`. Verify: parses.
- [ ] 4.4 Same for `2026-03-17-migrate-legacy-governance-to-openspec`. Verify: parses.
- [ ] 4.5 Same for `2026-03-25-add-log-brief-capability`. Verify: parses.
- [ ] 4.6 Same for `2026-03-26-add-exec-script-args`. Verify: parses.
- [ ] 4.7 Same for `2026-03-26-expand-next-step-guidance`. Verify: parses.
- [ ] 4.8 Same for `2026-03-26-surface-ctx-contract-in-exec-help`. Verify: parses.
- [ ] 4.9 Same for `2026-05-11-improve-cache-staleness-detection-and-examples`. Verify: parses.
- [ ] 4.10 Same for `2026-05-12-include-readme-in-upm-package`. Verify: parses.
- [ ] 4.11 Confirm each new file's `updated_at` is that change's own last real commit date, not today's date, and that every new `evidence` is scalar. Verify: no `updated_at` equals the current date unless the change was genuinely updated then.

## 5. Backfill the 4 partial files

- [ ] 5.1 Add `blocked_by: []` to `2026-03-26-exec-import-support`, with the justification recorded per Decision 2. Verify: parses.
- [ ] 5.2 Add `blocked_by: []` to `2026-03-26-readme-user-facing-rewrite`. Verify: parses.
- [ ] 5.3 Add `blocked_by: []` to `2026-05-12-exec-async-warning-status`. Verify: parses.
- [ ] 5.4 Add a scalar `evidence` value to `2026-05-14-relax-runtime-guidance-compile-count-situation` justified by that change's own proposal and tasks. Verify: parses.
- [ ] 5.5 Confirm no existing field in those 4 files was altered while adding the missing one. Verify: diff shows additions only.

## 6. Close the guard gaps

- [ ] 6.1 Delete `KNOWN_LEGACY_ARCHIVE_RECORDS` from `tests/test_openspec_change_meta.py`. Verify: no remaining reference to it.
- [ ] 6.2 Change the real-archive guard to assert that **no** failure is collected, with no exemptions. Verify: the guard is unconditional.
- [ ] 6.3 Add an assertion that every directory under `openspec/changes/archive/` has a `meta.yaml`. Verify: this assertion is what would have caught the 10.
- [ ] 6.4 Add an assertion, on raw text, that no archived `meta.yaml` uses list-form `evidence` (inline `[...]` or block `- item` under `evidence:`). Verify: it does not rely on parsed `ChangeMeta`.
- [ ] 6.5 Confirm the new assertions are non-vacuous by running each against a temporary fixture directory that violates it. Verify: each fails when it should.
- [ ] 6.6 Confirm `tools/openspec_change_meta.py` still accepts list form. Verify: no parser support was removed; the list-form parser tests still pass.
- [ ] 6.7 Update any test that referenced the legacy or list-form records by name. Verify: the suite passes.

## 7. Verify

- [ ] 7.1 Load every archived `meta.yaml` through `openspec_change_meta.load_meta` and confirm zero failures. Verify: printed parsed count equals the archive directory count, 0 failed.
- [ ] 7.2 Run `python -m unittest tests.test_openspec_change_meta tests.test_openspec_backlog`. Verify: OK.
- [ ] 7.3 Run the full default suite from `openspec/specs/validation-host-integration/how-to-run.md`. Verify: OK.
- [ ] 7.4 Run `python tools/openspec_backlog.py list` and compare with step 1.3. Verify: same output for non-archived changes.

## 8. Closeout

- [ ] 8.1 Confirm `git diff --stat` shows exactly 17 archived `meta.yaml` files plus the test and this change's artifacts. Verify: no other record touched.
- [ ] 8.2 Surface the inferred values to the human for review, since they are claims about past changes. Verify: presented before archive.
- [ ] 8.3 Complete the apply closeout review and state whether any new follow-up work was identified.
