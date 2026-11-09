# Tasks

## 1. Make the dependency list explicit

- [ ] 1.1 Create `requirements-test.txt` at the repository root naming `PyYAML`, the only
      third-party package imported by any selected test module. Verify: the file exists and
      `python -m pip install --dry-run -r requirements-test.txt` resolves PyYAML (or, offline,
      `python -c "import yaml"` succeeds afterwards on an interpreter that previously lacked it).

- [ ] 1.2 Add an install step to `.github/workflows/unit-tests.yml` immediately before the test
      step, running `python -m pip install --upgrade pip -r requirements-test.txt` with
      `shell: pwsh`. Verify: the workflow parses (`yaml.safe_load`), the module arguments are
      unchanged (still the same 24 modules), and the install step precedes the test step.

## 2. Make a missing dependency fail in CI

- [ ] 2.1 In `tests/test_package_layout.py`, convert the `ImportError` branch of
      `test_release_workflow_is_parseable_yaml_with_a_runnable_stamp_step` from an unconditional
      skip into `self.fail` when `os.environ.get("CI")` is set, keeping `skipTest` otherwise. The
      failure message must name PyYAML and `requirements-test.txt`. Verify: with PyYAML present the
      test passes; with `CI=1` and PyYAML made unimportable it fails naming PyYAML; without `CI`
      and PyYAML unimportable it skips.

- [ ] 2.2 Confirm no other selected module imports a third-party package, so the install step and
      this guard cover the whole dependency surface. Verify: an AST walk over `tests/`, `tools/`,
      and `cli/` reports `yaml` as the only non-stdlib, non-repository-local import.

## 3. Document the local setup

- [ ] 3.1 Update the mocked-layer section of
      `openspec/specs/validation-host-integration/how-to-run.md` to state that the default suite
      expects `python -m pip install -r requirements-test.txt`, and that a missing PyYAML skips one
      packaging assertion locally but fails under CI. Verify: the documented command line still
      parses to the same 24 modules and `python -m unittest tests.test_default_suite_selection`
      passes.

## 4. Regression

- [ ] 4.1 Run the full 24-module default suite locally with PyYAML installed. Verify: `OK`, 1048
      tests, and zero skips.

- [ ] 4.2 Simulate the CI environment without provisioning: run
      `tests.test_package_layout` with `CI=1` and PyYAML hidden from `sys.path`. Verify: the test
      fails with a message naming PyYAML, and the remaining `PreflightCompileCheck`-style tests in
      that module still report honestly rather than cascading.

- [ ] 4.3 Simulate the developer environment: run the same module with `CI` unset and PyYAML
      hidden. Verify: exactly one skip, naming PyYAML, and the rest of the module passes.

## Workflow follow-up

- Archive with `openspec archive make-ci-install-test-dependencies` once the pins are green.
- Verify the archived result: `openspec validate --all` and
  `python -m unittest tests.test_openspec_spec_hygiene`.
