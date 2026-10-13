## 1. Extract the shared splitter

- [ ] 1.1 Add `evidence_values(evidence: str) -> tuple[str, ...]` in `tools/openspec_backlog.py` that splits a joined value on `", "`, strips, and drops empties. Verify: it is the only place that splits.
- [ ] 1.2 Refactor `evidence_rank` to call `evidence_values` instead of splitting inline. Verify: `evidence_rank` contains no split logic.
- [ ] 1.3 Confirm `evidence_rank` still returns the same result for every case in the table above (single value, joined in order, joined out of order, empty). Verify: identical to current behavior; add pinning tests.

## 2. Fix the filter

- [ ] 2.1 Change `filter_records` to keep a record when `evidence in evidence_values(meta.evidence)`. Verify: a record with `evidence: tests, cli-transcript` matches `--evidence tests`.
- [ ] 2.2 Confirm matching is independent of value order. Verify: `tests, cli-transcript` and `cli-transcript, tests` both match `--evidence tests`.
- [ ] 2.3 Confirm a record with `evidence: tests` still matches `--evidence tests` and does not match `--evidence cli-transcript`. Verify: includes-match, not exact-set match (Decision 3).
- [ ] 2.4 Confirm a joined value supplied as the argument is rejected, per Decision 2. Verify: `--evidence "tests, cli-transcript"` errors via the existing argparse `choices`, and the rejection is pinned by a test.
- [ ] 2.5 Confirm filtering does not raise when a stored `evidence` contains an unrecognized value. Verify: the record is simply not matched, and `list` still completes.

## 3. Help text and cross-references

- [ ] 3.1 Update the `--evidence` argparse help to state the includes-match semantics, per Decision 5. Verify: `--help` output reflects it.
- [ ] 3.2 Correct the `define-evidence-as-multi-valued` artifact and, if it has already landed, the `AGENTS.md` pointer, so no documentation claims the exact-match behavior. Verify: no surviving text says the filter compares the whole string exactly.
- [ ] 3.3 Confirm `tools/openspec_backlog.py list --evidence <value>` runs against real non-archived changes and returns the expected set. Verify: matches the includes-match expectation for the current backlog.

## 4. Verify

- [ ] 4.1 Run `python -m unittest tests.test_openspec_backlog tests.test_openspec_change_meta`. Verify: OK.
- [ ] 4.2 Run the full default suite from `openspec/specs/validation-host-integration/how-to-run.md`. Verify: OK.
- [ ] 4.3 Confirm no other filter in `filter_records` was changed. Verify: `status`, `meta_status`, `change_type`, `priority`, `assumption_state`, and `backlog_only` behave as before.
- [ ] 4.4 Confirm ranking output order is unchanged for records with joined evidence. Verify: `list` ordering is identical before and after.

## 5. Closeout

- [ ] 5.1 Complete the apply closeout review and state whether any new follow-up work was identified.
- [ ] 5.2 Confirm `git diff` touches only `tools/openspec_backlog.py`, `tests/test_openspec_backlog.py`, and change artifacts. Verify: no record files changed.