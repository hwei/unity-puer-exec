## 1. Edit AGENTS.md

- [ ] 1.1 In the `AGENTS.md` change-metadata section, state that `evidence` is multi-valued and must name one or more values; an empty list is invalid. Verify: the bullet reads as a rule, not a description of code.
- [ ] 1.2 Document the three accepted input forms by example: `evidence: tests`, `evidence: [tests, manual-check]`, and a block list of `- item` lines. Verify: each form is shown literally.
- [ ] 1.3 Record that multiple values are stored and displayed joined with `", "` in written order, and that `dump_meta` emits that joined string as a scalar. Verify: the format string `", "` appears verbatim.
- [ ] 1.4 Record that ranking uses the strongest entry among the values, without restating the order table. Verify: `AGENTS.md` gains no table and no copy of `EVIDENCE_ORDER`.
- [ ] 1.5 Add a one-line pointer noting that the `--evidence` filter matches the whole string exactly and is tracked by `match-evidence-filter-on-multi-value`. Verify: the line names that change and does not present the behavior as intended.

## 2. Verify

- [ ] 2.1 Re-read every rule added in section 1 against `tools/openspec_change_meta.py` and `tools/openspec_backlog.py`, and confirm each stated rule matches the implementation. Verify: no rule is aspirational.
- [ ] 2.2 Confirm each stated rule is already pinned by an existing test in `tests/test_openspec_change_meta.py` or `tests/test_openspec_backlog.py`; if any rule is unpinned, add the pinning test. Verify: every rule has a corresponding assertion.
- [ ] 2.3 Run `python -m unittest tests.test_openspec_change_meta tests.test_openspec_backlog` and confirm no regression. Verify: OK.
- [ ] 2.4 Run `openspec validate define-evidence-as-multi-valued --strict`. Verify: valid.

## 3. Closeout

- [ ] 3.1 Confirm `git diff` touches only `AGENTS.md` and this change's artifacts. Verify: no code or record file changed.
- [ ] 3.2 Complete the apply closeout review and state whether any new follow-up work was identified.