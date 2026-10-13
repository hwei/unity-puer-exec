## 1. Establish the baseline

- [ ] 1.1 Re-run the measurement in design.md (archive directory count, records with no `meta.yaml`, records with a partial `meta.yaml`) and confirm it still matches: 134 directories, 10 with no file, 4 partial. Verify: the numbers are current, not copied from the proposal.
- [ ] 1.2 For each of the 14 target records, gather its own evidence: `proposal.md`, `tasks.md` completion state, and last real commit date. Verify: every record has all three before any field is written.
- [ ] 1.3 Record the inferred value and its justification for each of the 14 in a table in design.md, as each is decided. Verify: no row says only "inferred".

## 2. Backfill the 10 missing files

- [ ] 2.1 Write `meta.yaml` for `2026-03-17-add-apply-closeout-governance`, with `change_type`, `priority`, `blocked_by`, `assumption_state`, `evidence`, and `updated_at` justified by its proposal. Verify: it parses via `openspec_change_meta.load_meta`.
- [ ] 2.2 Same for `2026-03-17-archive-legacy-decisions`. Verify: parses.
- [ ] 2.3 Same for `2026-03-17-delete-legacy-docs`. Verify: parses.
- [ ] 2.4 Same for `2026-03-17-migrate-legacy-governance-to-openspec`. Verify: parses.
- [ ] 2.5 Same for `2026-03-25-add-log-brief-capability`. Verify: parses.
- [ ] 2.6 Same for `2026-03-26-add-exec-script-args`. Verify: parses.
- [ ] 2.7 Same for `2026-03-26-expand-next-step-guidance`. Verify: parses.
- [ ] 2.8 Same for `2026-03-26-surface-ctx-contract-in-exec-help`. Verify: parses.
- [ ] 2.9 Same for `2026-05-11-improve-cache-staleness-detection-and-examples`. Verify: parses.
- [ ] 2.10 Same for `2026-05-12-include-readme-in-upm-package`. Verify: parses.
- [ ] 2.11 Confirm each new file's `updated_at` is that change's own last real commit date, not today's date. Verify: no `updated_at` equals the current date unless the change was genuinely updated then.

## 3. Backfill the 4 partial files

- [ ] 3.1 Add `blocked_by: []` to `2026-03-26-exec-import-support`, with the justification recorded per Decision 2. Verify: parses.
- [ ] 3.2 Add `blocked_by: []` to `2026-03-26-readme-user-facing-rewrite`. Verify: parses.
- [ ] 3.3 Add `blocked_by: []` to `2026-05-12-exec-async-warning-status`. Verify: parses.
- [ ] 3.4 Add an `evidence` value to `2026-05-14-relax-runtime-guidance-compile-count-situation` justified by that change's own proposal and tasks. Verify: parses.
- [ ] 3.5 Confirm no existing field in those 4 files was altered while adding the missing one. Verify: diff shows additions only.

## 4. Close the guard gaps

- [ ] 4.1 Delete `KNOWN_LEGACY_ARCHIVE_RECORDS` from `tests/test_openspec_change_meta.py`. Verify: no remaining reference to it.
- [ ] 4.2 Change the real-archive guard to assert that **no** failure is collected, with no exemptions. Verify: the guard is unconditional.
- [ ] 4.3 Add an assertion that every directory under `openspec/changes/archive/` has a `meta.yaml`. Verify: this assertion is what would have caught the 10.
- [ ] 4.4 Confirm both new assertions are non-vacuous by running them against a temporary fixture directory that violates each. Verify: each fails when it should.
- [ ] 4.5 Update any test that referenced the four legacy records by name. Verify: the suite passes.

## 5. Verify

- [ ] 5.1 Load all 134 archived `meta.yaml` files through `openspec_change_meta.load_meta` and confirm zero failures. Verify: printed count is 134 parsed, 0 failed.
- [ ] 5.2 Run `python -m unittest tests.test_openspec_change_meta tests.test_openspec_backlog`. Verify: OK.
- [ ] 5.3 Run the full default suite from `openspec/specs/validation-host-integration/how-to-run.md`. Verify: OK.
- [ ] 5.4 Run `python tools/openspec_backlog.py list` and confirm it is unaffected. Verify: same output as before the backfill for non-archived changes.
- [ ] 5.5 Confirm `normalize-archived-list-evidence-records` has landed, so its canonical-form assertion is not contradicted by these new files. Verify: no archived record uses list-form `evidence`.

## 6. Closeout

- [ ] 6.1 Confirm `git diff --stat` shows exactly 14 archived `meta.yaml` files plus the test and this change's artifacts. Verify: no other record touched.
- [ ] 6.2 Surface the inferred values to the human for review, since they are claims about past changes. Verify: presented before archive.
- [ ] 6.3 Complete the apply closeout review and state whether any new follow-up work was identified.