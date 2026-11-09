# Tasks

## 1. Prove the five modules belong in the mocked layer

- [x] 1.1 Confirm, in a checkout with no `.env` and `UNITY_PROJECT_PATH` unset, that the five
      unselected mocked modules run without a Unity Editor or a validation host:
      `tests.test_fake_user32`, `tests.test_unity_modal_blockers`, `tests.test_real_host_retry`,
      `tests.test_release_openupm_tool`, `tests.test_response_file_output`. Verify: from a
      `git archive HEAD` extraction (not the working tree, which has a local `.env`), running
      `env -u UNITY_PROJECT_PATH python -m unittest <five modules>` reports tests run and `OK`,
      with no skip and no Unity-specific failure.
- [x] 1.2 Record the disposition in this change directory: each module either "belongs in the
      mocked layer, select it" or "needs the real host, exclude it with a reason". The design's
      exclusion table assumes only `tests.test_real_host_integration` is excluded; if 1.1
      contradicts that for any module, update `design.md` and this change's spec delta before
      continuing. Verify: a written disposition naming all five modules, and `design.md` D2/`D3`
      unchanged or amended to match.

## 2. Select the modules in both lists

- [x] 2.1 Add the five modules confirmed in 1.1 to the module arguments in
      `.github/workflows/unit-tests.yml`, at their alphabetical positions in the existing list.
      Verify: `grep -c "tests.test_fake_user32" .github/workflows/unit-tests.yml` returns `1`, and
      the workflow YAML still parses.
- [x] 2.2 Add the same five modules, at the same alphabetical positions, to the documented
      default-suite command line in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify:
      `python -m unittest tests.test_default_suite_selection` passes (the existing set-equality
      property now covers 24 modules per side).

## 3. Close the blind spot in the guard

- [x] 3.1 Add the on-disk enumeration property to `tests/test_default_suite_selection.py`: derive
      `tests.test_*` module names from `REPO_ROOT / "tests" / "test_*.py"`, subtract the union of
      the two parsed lists, and assert the remainder equals the keys of a module-level
      `EXCLUSIONS` mapping. Assert every exclusion reason is a non-empty string, and that no
      exclusion is also a selected module. Verify: `python -m unittest
      tests.test_default_suite_selection` passes.
- [x] 3.2 Reduce the existing `test_real_host_integration_is_not_a_selected_module` case to what
      the new property does not already state, or delete it if the new property fully covers it —
      do not leave two assertions of the same fact under different names. Verify: the module still
      fails if `tests.test_real_host_integration` is added to either list (checked in 3.3).
- [x] 3.3 Mutation probe: in a scratch copy (never the working tree), (a) add a new
      `tests/test_*.py` module that appears in neither list, (b) delete one of the five modules
      from **both** lists, (c) remove the single exclusion entry, and (d) add an exclusion entry
      for a module that is actually selected. Each mutant must make a named test in
      `DefaultSuiteSelectionTests` fail, and the failure must name the offending module. Verify:
      the probe reports every mutant caught; record the mutant count in this task.

## 4. Regression

- [x] 4.1 Run the full 24-module default suite as documented in
      `openspec/specs/validation-host-integration/how-to-run.md`. Verify: every listed module
      passes with no new failure or skip, and the run count is the previous 912 plus the 134
      recovered cases.
- [x] 4.2 Run the same 24-module set on a Python 3.12 interpreter matching the CI pin. Verify:
      `OK`, no failure caused by the 3.9 → 3.12 difference; note any interpreter-sensitive
      behavior observed.

## Workflow follow-up

- Archive with `openspec archive select-every-mocked-test-module` once the pins are green.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
