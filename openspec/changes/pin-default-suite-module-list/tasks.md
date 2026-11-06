# Tasks

## 1. Settle the disposition of the drifted module

- [x] 1.1 Confirm `tests/test_real_host_reset.py` is mocked-layer: it imports
      `tests.test_real_host_integration` but drives it under `unittest.mock` and must require
      neither a Unity Editor nor a validation host. Verify by running it with no host configured
      and no Editor reachable — `python -m unittest tests.test_real_host_reset` from a shell
      where `UNITY_PROJECT_PATH` is unset — and confirming it reports tests run rather than
      skipping wholesale.
- [x] 1.2 Record the disposition in the change directory: either "belongs in CI, the workflow
      list is missing it" or "belongs out of CI, the documented list is wrong". The two
      directions imply opposite fixes for task 2.1, so this must be settled first and written
      down rather than inferred later.

## 2. Make the two lists the same set

- [x] 2.1 Apply the disposition from 1.2 to whichever list is wrong. If the workflow is the
      deficient one, add `tests.test_real_host_reset` to the module arguments in
      `.github/workflows/unit-tests.yml` in the list's existing order. Verify the workflow YAML
      still parses and the module appears exactly once:
      `grep -c "tests.test_real_host_reset" .github/workflows/unit-tests.yml` returns `1`.
- [x] 2.2 Add a mocked-layer test that parses the module arguments out of
      `.github/workflows/unit-tests.yml` and the module names out of the documented default-suite
      command line in `openspec/specs/validation-host-integration/how-to-run.md`, and asserts the
      two sets are equal. Verify it passes on the corrected lists:
      `python -m unittest tests.test_default_suite_selection` (new module).
- [x] 2.3 Prove the comparison has teeth: in a scratch copy, drop one module from each list in
      turn and verify the test fails and names the missing module both ways. Record the two
      failure messages in the change directory.
- [x] 2.4 Confirm the test does not read a third representation — it must parse the workflow and
      the doc as they are written. Verify by inspection that the module contains no hardcoded
      expected list, only the two parsed inputs and a set comparison.

## 3. Wire the new test into both lists

- [x] 3.1 Add the new module from 2.2 to the unit-test workflow's module arguments and to the
      documented command line in the same commit, and verify both lists still agree by re-running
      the comparison test — this is the first real exercise of the guard it installs.
- [x] 3.2 Run the mocked default suite as documented and verify `OK` with no new failures, and
      that the run now includes `tests.test_real_host_reset`.

## 4. Closeout readiness

- [x] 4.1 Run `openspec validate pin-default-suite-module-list --strict` and verify it passes.
- [ ] 4.2 Verify the CI workflow actually executes the corrected selection: trigger it on a
      branch or read the run log for the added module, so the fix is evidenced by a real CI run
      rather than only by a local invocation. Record the run in the change directory.
- [ ] 4.3 Write the closeout finding summary stating either `No new follow-up work identified`
      or `New follow-up candidates identified`.

## Workflow follow-up

- Archive with `openspec archive pin-default-suite-module-list` once review requirements are
  satisfied, then verify `openspec/specs/unit-test-github-action/spec.md` carries the amended
  requirement and the new comparison requirement.
- If task 1.2 concludes the documented list was the wrong one, the same reasoning should be
  applied to any other module that appears in only one list, since the comparison test will name
  them all at once.
