## 1. Make the two requirements verifiable

- [ ] 1.1 Add the `repository-governance` MODIFIED delta giving `Apply-closeout findings require human discussion before promotion` a `SHALL`/`MUST` sentence and at least one scenario, keeping its pointer to the canonical apply-closeout-review requirement. Verify: `openspec validate repository-governance --type spec` no longer reports an error for it.
- [ ] 1.2 Do the same for `Superseded changes are archived rather than deleted`, keeping its pointer to the canonical change-backlog-triage requirement. Verify: the same validation reports no error for either requirement.

## 2. Guard against drift

- [ ] 2.1 Add `tests/test_openspec_spec_hygiene.py` asserting that every requirement in `openspec/specs/**/spec.md` has at least one `#### Scenario:` and contains `SHALL` or `MUST`. Verify: the test passes on the current tree and fails when a scenario or the keyword is removed from a fixture requirement.
- [ ] 2.2 Register the new module in the default unit-test suite (`.github/workflows/unit-tests.yml` and the run instructions). Verify: the default suite list includes it and the module runs with no Unity or `openspec` CLI present.

## 3. Closeout

- [ ] 3.1 Confirm `openspec validate --all` reports no failed durable spec and the mocked suite passes. Verify: the validation totals show no failed spec and the suite run is green.
- [ ] 3.2 Record the before/after validator output in the change's evidence and archive. Verify: the record states the two previously failing requirements now validate.
