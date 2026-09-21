### Spec-hygiene evidence — 2026-09-21 (harden-repository-governance-spec)

Scope: the two pointer requirements in `openspec/specs/repository-governance/spec.md`
that failed the OpenSpec validator, and the structural guard added to the default unit
suite.

Commands:

```
openspec validate repository-governance --type spec
openspec validate --all
python -m unittest tests.test_openspec_spec_hygiene
```

#### Before (recorded at apply start, on `3c7c89d`)

`openspec validate repository-governance --type spec`:

```
Specification 'repository-governance' has issues
✗ [ERROR] requirements.4.scenarios: Requirement must have at least one scenario
✗ [ERROR] requirements.10.scenarios: Requirement must have at least one scenario
⚠ [WARNING] requirements[4].scenarios: Requirement must have at least one scenario. Scenarios must use level-4 headers. Convert bullet lists into:
#### Scenario: Short name
- **WHEN** ...
- **THEN** ...
- **AND** ...
⚠ [WARNING] requirements[10].scenarios: Requirement must have at least one scenario. Scenarios must use level-4 headers. Convert bullet lists into:
#### Scenario: Short name
- **WHEN** ...
- **THEN** ...
- **AND** ...
⚠ [WARNING] requirements[4]: Requirement "Apply-closeout findings require human discussion before promotion" should contain SHALL or MUST (RFC 2119 best practice for English specs)
⚠ [WARNING] requirements[10]: Requirement "Superseded changes are archived rather than deleted" should contain SHALL or MUST (RFC 2119 best practice for English specs)
```

`openspec validate --all`:

```
Totals: 31 passed, 1 failed (32 items)
Details: openspec validate repository-governance --type spec
```

#### After (durable spec updated from the change's MODIFIED delta)

`openspec validate repository-governance --type spec`:

```
Specification 'repository-governance' is valid
```

`openspec validate --all`:

```
Totals: 32 passed, 0 failed (32 items)
```

The two previously failing requirements — `Apply-closeout findings require human
discussion before promotion` (requirements[4]) and `Superseded changes are archived
rather than deleted` (requirements[10]) — now carry a `SHALL`/`MUST` sentence and at
least one `#### Scenario:` each, and both validate. The canonical cross-references to
`apply-closeout-review` Requirement 3 and `change-backlog-triage` Requirement 10 are
preserved.

#### Guard

`tests/test_openspec_spec_hygiene.py` scans `openspec/specs/**/spec.md` and reports a
violation for any requirement without a `#### Scenario:` block or without a
`SHALL`/`MUST` in its normative text. Evidence:

- The guard reports no violation across all 293 durable requirements on the updated
  tree (the pre-update tree tripped it on exactly the two requirements above).
- Fixture cases prove it fails when the scenario is removed and when the keyword is
  removed from a requirement.
- `python -m unittest tests.test_openspec_spec_hygiene` — 5 tests, OK.
- The module imports only `re`, `unittest`, and `pathlib`; verified it passes with the
  `openspec` CLI removed from `PATH`.

#### Default suite

```
python -m unittest tests.test_cleanup_validation_host_tool tests.test_cli_version
  tests.test_direct_exec_client tests.test_editor_log_isolation
  tests.test_openspec_backlog tests.test_openspec_change_meta
  tests.test_openspec_spec_hygiene tests.test_package_layout
  tests.test_prepare_validation_host_tool tests.test_refresh_change_signal
  tests.test_unity_log_brief tests.test_unity_puer_session tests.test_unity_session
  tests.test_unity_session_cli tests.test_unity_session_modules
```

Result: `Ran 488 tests ... OK`. `tests.test_openspec_spec_hygiene` is registered in
`.github/workflows/unit-tests.yml` and in
`openspec/specs/validation-host-integration/how-to-run.md`, and the run docs state the
guard mirrors only the two structural rules while `openspec validate --all` remains the
authority for full validation.
