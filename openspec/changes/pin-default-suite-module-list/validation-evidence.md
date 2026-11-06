# Validation Evidence — pin-default-suite-module-list

## 1.1 / 1.2 Disposition of `tests.test_real_host_reset`

**Condition:** `UNITY_PROJECT_PATH` unset in the shell (this worktree has no `.env`), no Unity
Editor running, no validation host prepared.

**Command:**

```
$ echo "UNITY_PROJECT_PATH=[${UNITY_PROJECT_PATH}]"      # -> UNITY_PROJECT_PATH=[]
$ ls .env                                                 # -> No such file or directory
$ python -m unittest tests.test_real_host_reset
```

**Result:**

```
Ran 22 tests in 0.805s

OK
```

22 tests executed and passed — the module does not skip wholesale. It imports
`tests.test_real_host_integration` only to obtain `_SharedRealHostDevice` and its helpers, then
drives them under `unittest.mock` (`mock.patch.object(real_host.unity_session, "_probe_health")`,
`mock.patch.object(real_host, "_scan_ready_control_endpoint")`, `mock.patch.object(device,
"_exec_settled")`, …). No test in the module talks to a live Editor or a host project.

**Disposition: `belongs in CI, the workflow list is missing it`.**

`tests.test_real_host_reset` is a mocked-layer module. The documented default-suite command line
was correct; `.github/workflows/unit-tests.yml` was the deficient list, so task 2.1 adds the
module to the workflow (not the reverse). This matches the amended requirement's scenario
"A mocked module that imports the real-host suite still belongs in CI": the *import* of
`tests/test_real_host_integration.py` is fine, selecting it as a module is not.

## 2.1 Workflow fix

```
$ grep -c "tests.test_real_host_reset" .github/workflows/unit-tests.yml
1
```

`yaml.safe_load` on the corrected workflow still parses; the `unit-tests` job keeps its three
steps and the module appears exactly once, inserted between `tests.test_puerts_version_compat`
and `tests.test_refresh_change_signal` (the list's existing alphabetical order).

## 2.2 Comparison test green on the corrected lists

```
$ python -m unittest tests.test_default_suite_selection
...
Ran 3 tests in 0.003s

OK
```

(Before the fix, the same test failed on the pre-existing drift:
`AssertionError: Items in the second set but not the first: 'tests.test_real_host_reset'`.)

## 2.3 The comparison has teeth

Scratch copy under `.tmp/teeth/` (workflow + doc + `tests/` copied out; the real lists were never
left broken). One module was dropped from each list in turn.

### Case A — module present in the documented list only

Removed the `tests.test_real_host_reset` argument line from the scratch workflow, then ran
`python -m unittest tests.test_default_suite_selection`:

```
AssertionError: Items in the second set but not the first:
'tests.test_real_host_reset' : The CI module list and the documented default-suite command line must name the same set of test modules:
tests.test_real_host_reset is in the documented default suite but missing from the CI workflow
```

### Case B — module present in CI only

Restored the scratch workflow, removed `tests.test_unity_session` from the scratch documented
command line, then ran the same command:

```
AssertionError: Items in the first set but not the second:
'tests.test_unity_session' : The CI module list and the documented default-suite command line must name the same set of test modules:
tests.test_unity_session is in the CI workflow but missing from the documented default suite
```

Both directions fail and both name the one-sided module. The spec's two scenarios ("added to the
documented list only", "added to CI only") are covered.

## 2.4 No third representation

`tests/test_default_suite_selection.py` contains no expected module list. It holds only:

- two path constants (`WORKFLOW_PATH`, `HOW_TO_RUN_PATH`),
- `parse_workflow_modules()` — finds the `python -m unittest` line in the workflow and joins its
  PowerShell backtick continuations,
- `parse_documented_modules()` — finds the `python -m unittest` line inside a fenced block in
  `how-to-run.md`,
- `describe_disagreement()` — set difference between the two parsed lists, for the message,
- three assertions: both parses are non-empty and duplicate-free, the two sets are equal, and
  `tests.test_real_host_integration` is not a *selected* module in either list.

`test_both_lists_are_actually_parsed` exists so a parse that silently returns nothing cannot make
the equality pass vacuously. The only hardcoded module string is the excluded
`tests.test_real_host_integration`, an invariant of the requirement rather than an expected list.

## 3.1 New module wired into both lists

`tests.test_default_suite_selection` was added to both the workflow module arguments and the
documented command line, then the comparison test was re-run:

```
Ran 3 tests in 0.003s

OK
```

## 3.2 Documented default suite run

The exact command line at `openspec/specs/validation-host-integration/how-to-run.md:9` was
executed from a shell with `UNITY_PROJECT_PATH` unset:

```
$ CMD=$(sed -n '9p' openspec/specs/validation-host-integration/how-to-run.md)
$ env -u UNITY_PROJECT_PATH $CMD
```

Output:

```
Ran 855 tests in 69.370s

OK
```

(Preceded by one pre-existing, unrelated stderr line from `tests.test_unity_session`:
`unity-puer-session: error: argument command: invalid choice: 'ensure-ready' (choose from 'wait-for-log-pattern')` — a test asserting the CLI rejects a removed subcommand; not a failure.)

`tests.test_real_host_reset` is inside that run — the loaded test count is the evidence, computed
without running the suite a second time:

```
$ python -c "load tests for the parsed documented module list, with and without test_real_host_reset"
documented modules: 19
tests loaded with the documented list: 855
tests loaded without tests.test_real_host_reset: 833
delta from tests.test_real_host_reset: 22
tests.test_real_host_reset selected: True
```

855 matches the suite's reported total, and the 22-test delta matches the 22 tests task 1.1 ran
in `tests.test_real_host_reset` on its own. No new failures: `OK`.

Task 4.2 note: the same 855-test count is what the CI log must also report, since CI now runs
the identical set.

## 4.1 OpenSpec strict validation

```
$ MSYS_NO_PATHCONV=1 openspec validate pin-default-suite-module-list --strict
Change 'pin-default-suite-module-list' is valid
```

## 4.2 Real CI run

PENDING-4.2

## 4.3 Closeout finding summary

PENDING-4.3
