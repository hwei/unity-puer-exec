## 1. Extract the shared splitter

- [ ] 1.1 Add `evidence_values(evidence: str) -> tuple[str, ...]` in `tools/openspec_backlog.py` that splits on `,`, strips, and drops empties. Verify: it is the only place in the tool that splits an `evidence` string.
- [ ] 1.2 Refactor `evidence_rank` to call `evidence_values` instead of splitting inline. Verify: `evidence_rank` contains no split logic.
- [ ] 1.3 Pin `evidence_rank` results for a single value, a joined value in order, a joined value out of order, an unknown value, and an empty string. Verify: identical to current behavior.

## 2. Fix the filter

- [ ] 2.1 Change `filter_records` to keep a record when `evidence in evidence_values(meta.evidence)`. Verify: a record with `evidence: tests, cli-transcript` matches `--evidence tests`.
- [ ] 2.2 Confirm matching is independent of value order. Verify: `tests, cli-transcript` and `cli-transcript, tests` both match `--evidence tests`.
- [ ] 2.3 Confirm a record with `evidence: tests` still matches `--evidence tests` and does not match `--evidence cli-transcript`. Verify: includes-match, not exact-set match (Decision 6).
- [ ] 2.4 Add `choices=tuple(EVIDENCE_ORDER)` to `--evidence`, and pin with a test that `--evidence "tests, cli-transcript"` is rejected by argparse. Verify: the rejection is asserted, not incidental.
- [ ] 2.5 Confirm filtering does not raise when a stored `evidence` contains an unrecognized value. Verify: the record is simply not matched, and `list` still completes.
- [ ] 2.6 Update the `--evidence` help text to state the includes-match semantics. Verify: `--help` output reflects it.

## 3. Edit AGENTS.md

- [ ] 3.1 In the change-metadata section, state that `evidence` is multi-valued and must name one or more values; an empty list is invalid. Verify: the bullet reads as a rule, not a description of code.
- [ ] 3.2 State that the canonical written form is scalar — `evidence: tests` or `evidence: tests, manual-check` — joined with `", "` in written order, and that the parser also accepts inline `[a, b]` and block `- a` list forms. Verify: the format string `", "` appears verbatim and the canonical form is named as such.
- [ ] 3.3 Record that ranking uses the strongest entry among the values, without restating the order table. Verify: `AGENTS.md` gains no table and no copy of `EVIDENCE_ORDER`.
- [ ] 3.4 If `--evidence` is mentioned, describe it as includes-match over one value. Verify: no text describes exact whole-string matching or points to a pending fix.

## 4. Verify

- [ ] 4.1 Re-read every rule added in section 3 against `tools/openspec_change_meta.py` and `tools/openspec_backlog.py`. Verify: no rule is aspirational.
- [ ] 4.2 Confirm each stated rule is pinned by a test in `tests/test_openspec_change_meta.py` or `tests/test_openspec_backlog.py`; add the pinning test for any unpinned rule. Verify: every rule has a corresponding assertion.
- [ ] 4.3 Confirm no other filter in `filter_records` changed. Verify: `status`, `meta_status`, `change_type`, `priority`, `assumption_state`, and `backlog_only` behave as before.
- [ ] 4.4 Run `python tools/openspec_backlog.py list` and `list --evidence <value>` against real non-archived changes. Verify: ordering is unchanged and the filtered set matches includes-match.
- [ ] 4.5 Run `python -m unittest tests.test_openspec_backlog tests.test_openspec_change_meta`. Verify: OK.
- [ ] 4.6 Run the full default suite from `openspec/specs/validation-host-integration/how-to-run.md`. Verify: OK.
- [ ] 4.7 Run `openspec validate define-evidence-as-multi-valued --strict`. Verify: valid.

## 5. Closeout

- [ ] 5.1 Confirm `git diff` touches only `AGENTS.md`, `tools/openspec_backlog.py`, the two test files, and this change's artifacts. Verify: no record file changed.
- [ ] 5.2 Complete the apply closeout review and state whether any new follow-up work was identified.
