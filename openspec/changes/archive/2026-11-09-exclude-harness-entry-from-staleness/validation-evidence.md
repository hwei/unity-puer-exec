# Validation evidence: exclude-harness-entry-from-staleness

Scope of this file: the evidence behind every checked-off task in `tasks.md`.
Before/after pair for task 4.1, control direction for 4.2, both hosts for 4.3,
the archived regression pair for 4.4, and the mocked layers for group 3.

Working tree at time of writing: branch `main`, base commit `de9b05c`.
Nothing was committed, archived, or merged.

---

## Task 4.1 — before/after pair (the proof the change does anything)

Case: `tests.test_real_host_integration.RealHostIntegrationTests.test_import_base_url_preserves_globals_across_execs_against_real_host`

Two successive execs sharing one filesystem `--import-base-url` fixture directory.
The first seeds a marker on `ctx.globals`, the second reads it back. The assertion
is that the second response carries **no** `recovery` block and the marker survives.

### BEFORE (unmodified server; only the new test present)

`git checkout -- packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`
with the new case already in `tests/test_real_host_integration.py`. Host: 2.2.2
(`c3-client-tree2/Project`). Raw log: `.tmp/ehefs/before-tree2-run.log`,
launch record: `.tmp/ehefs/before-tree2-launches.json`.

```
test_import_base_url_preserves_globals_across_execs_against_real_host ... FAIL
AssertionError: {'performed': True, 'type': 'jsenv_reset', 'reason': 'module_cache_stale',
'policy': 'auto-reset',
'affected_modules': ['F:/C3/unity-puer-exec-workspace/c3-client-tree2/Project/Assets/__codex_validation_temp/import_fixture~/__puer_exec_entry_ae89f1fd78c148028b78350074e4fb95.js']} is not None
: a filesystem --import-base-url reset the JsEnv by itself: {... 'result': {'marker': None,
'greeting': 'resolved-through-import-base-url'},
'recovery': {'performed': True, 'type': 'jsenv_reset', 'reason': 'module_cache_stale',
'policy': 'auto-reset',
'affected_modules': ['.../import_fixture~/__puer_exec_entry_ae89f1fd78c148028b78350074e4fb95.js']} ...}

Ran 1 test in 90.289s
FAILED (failures=1)
```

This is exactly the defect: `reason=module_cache_stale` naming a
`__puer_exec_entry_*.js` path, `result.marker == null` because the JsEnv was reset.

### AFTER (the fix)

Same case, same host, unmodified test, run together with the 4.2 control case:

```
test_import_base_url_preserves_globals_across_execs_against_real_host ... ok
test_import_base_url_still_detects_a_changed_caller_module_against_real_host ... ok

Ran 2 tests in 120.111s
OK
```

Raw log: `.tmp/ehefs/after-tree2-run.log`, launch record:
`.tmp/ehefs/after-tree2-launches.json`.

The pair is what makes the change proven: same test, same host, fails with the
entry file named in `affected_modules` before the fix and passes after it.

---

## Task 4.2 — control direction (the exclusion did not widen)

Case: `...test_import_base_url_still_detects_a_changed_caller_module_against_real_host`

One exec imports `changing.js` from the filesystem base; the file is rewritten;
a second exec with the same base must report `recovery.reason ==
"module_cache_stale"` with `affected_modules` naming `changing.js`, and the new
module value must be what runs. Included in the after-run above: `ok`.

```
test_import_base_url_still_detects_a_changed_caller_module_against_real_host ... ok
```

The assertion is on `reason == "module_cache_stale"` **and** the path suffix
`changing.js` in `affected_modules`, so "nothing in a base directory is tracked"
cannot pass it.

### Mocked restatement of the same boundary (EditMode)

`packages/com.txcombo.unity-puer-exec/Tests/EditMode/UnityPuerExecHarnessOwnedModuleTests.cs`:

| Case | Decision pinned |
|---|---|
| `HarnessOwnedPathReadByTheLoaderIsNotRecorded` | a recorded harness path never enters the ledger |
| `HarnessOwnedEntryIsNotStaleAfterTheSweepDeletesIt` | the exact before/after failure, in miniature |
| `CallerModuleInTheSameDirectoryIsStillRecorded` | a caller file in the base dir becomes stale when deleted |
| `CallerFileWithTheEntryPrefixOutsideAServerWrittenBaseIsStillRecorded` | prefix alone does not exclude |
| `CallerFileWithTheEntryPrefixInsideAServerWrittenBaseIsStillRecorded` | the spec's hard case: prefix **and** in the base dir is still tracked |
| `RemovedCallerModuleIsStillStaleAndStillReported` | durable requirement "Removed loaded module is stale" |
| `CallerModuleWithAMovedMtimeIsStillStale` | durable requirement "modified is stale" |
| `FilesystemEntrySpecifierIsRegisteredForAWrittenHarnessModule` | design Risk 1: the write site registers ownership |

### Note: the fallback was narrowed during apply

Design D2 called for a name fallback of "prefix + a base directory this process
wrote into". The `cache-staleness-detection` delta requires the stronger,
contradicting case: *"the caller has their own module in that same directory,
including one whose name begins with `__puer_exec_entry_`"* is still tracked. A
prefix+directory rule cannot satisfy that. The fallback therefore matches the
**exact generated entry file name** last written into that directory
(`LastHarnessEntryFileNameByDirectory`), which satisfies both: a lost-membership
harness entry is still excluded, and a caller file that merely shares the prefix
is still tracked. Pinned by `CallerFileWithTheEntryPrefixInsideAServerWrittenBaseIsStillRecorded`.

`CheckModuleStaleness` itself is untouched apart from `private` -> `internal` for
test access: the missing-or-moved rule and the `affected_modules` projection are
byte-identical, and `test_package_layout.py` now asserts that (no
`IsHarnessOwnedModulePath` inside the staleness method, and both branches present).

---

## Task 4.3 — both hosts

### 2.2.2 host — `F:/C3/unity-puer-exec-workspace/c3-client-tree2/Project`

`prepare_validation_host.py --dry-run` -> `status: unchanged`,
`embedded_package_shadowing: false`, `package_testable: true` (wired by `file:`).

| Run | Cases | Result | Log |
|---|---|---|---|
| before | 4.1 case | `FAILED (failures=1)` | `.tmp/ehefs/before-tree2-run.log` |
| after | 4.1 + 4.2 | `Ran 2 tests ... OK` | `.tmp/ehefs/after-tree2-run.log` |
| 4.4 regression | the archived two | `Ran 2 tests in 97.577s ... OK` | console transcript in this file |

Launch record (`.tmp/ehefs/after-tree2-launches.json`):
`interactive_launch_count: 1`, `batch_preflight_launches: 1`.

Host status: the 2.2.2 host was **already dirty before this change**
(`M Project/Packages/manifest.json`, `M Project/Packages/packages-lock.json`, plus
pre-existing untracked scratch logs), and its status is unchanged by these runs;
no new path appeared and `Project/Assets/__codex_validation_temp` does not exist
afterwards (the suite's per-case cleanup removed the fixture and the swept entry
files with it).

### 3.0.0 host — `F:/C3/c3-client-tree5/Project`

Repository-owned sequence, all through `tools/prepare_validation_host.py`:

```
ensure-closed                     -> already_stopped
--clear-embedded-shadow           -> status: cleared
                                     backup: Project/.unity-puer-exec-embedded-backup/
                                             com.txcombo.unity-puer-exec-20261109
                                     embedded_package_shadowing: false
plain prepare                     -> status: updated, package_testable: true,
                                     embedded_package_shadowing: false
run the four cases                -> OK (below)
--restore-embedded-shadow         -> status: restored,
                                     moved .../com.txcombo.unity-puer-exec-20261109 ->
                                     Project/Packages/com.txcombo.unity-puer-exec
--restore-manifest                -> status: restored,
                                     moved manifest.json + packages-lock.json,
                                     left_in_place: []
```

Four cases (both new ones and both archived regression ones) in one launch,
against the **final** tree:

```
test_import_base_url_preserves_globals_across_execs_against_real_host ... ok
test_import_base_url_still_detects_a_changed_caller_module_against_real_host ... ok
test_exec_resolves_relative_import_through_import_base_url_against_real_host ... ok
test_reset_jsenv_before_exec_clears_globals_with_an_unchanged_module_against_real_host ... ok

Ran 4 tests in 142.385s
OK
```

Raw log: `.tmp/ehefs/tree5-final-verbose.log` (4 `... ok` lines).
Launch record from the preceding identical-selection run:
`.tmp/ehefs/tree5-final-launches.json` — `interactive_launch_count: 1`,
`new_unity_process_count: 3` (one interactive Editor + two batch preflight
processes; the two preflights are the suite-level compile check and the CLI's own
launch-time check, not per-case launches).

Host state after restore, checked with the command tasks.md names:

```
git -C F:/C3/c3-client-tree5 status --short     -> (empty)
ls -d Project/.unity-puer-exec-*                -> no such file
```

> **Discarded measurement.** The first 3.0.0 run
> (`.tmp/ehefs/tree5-overlapped-run.log`) also finished `OK`, but it overlapped an
> edit to the package source made while it was running, so its Editor may have
> compiled a different revision than the one under review. It is kept only as a
> record and is **not** the evidence. The run above was executed after the final
> edit, and no package file changed after it started.

---

## Task 4.4 — archived regression pair, both hosts

Both cases from the archived `cover-import-and-reset-jsenv-real-host` change:

```
tests.test_real_host_integration.RealHostIntegrationTests.test_exec_resolves_relative_import_through_import_base_url_against_real_host
tests.test_real_host_integration.RealHostIntegrationTests.test_reset_jsenv_before_exec_clears_globals_with_an_unchanged_module_against_real_host
```

- 2.2.2: `Ran 2 tests in 97.577s` / `OK`, one interactive launch + one preflight.
- 3.0.0: both included in the four-case `OK` run above.

The reset case's discrimination is unaffected: it still asserts
`recovery.reason == "explicit_request"`, a value only the flag can produce, and
the unchanged-module baseline still holds (its execs are inline, so they never
touch the entry-file path this change touches).

---

## Group 3 — mocked layers

### EditMode (Unity-side, 2.2.2 host)

```
python tools/run_editmode_tests.py
{"status": "passed", "kind": null, "exit_code": 0, "total": 29, "passed": 29,
 "failed": 0, "skipped": 0, "inconclusive": 0, "failed_tests": []}
```

8 of the 29 are the new `UnityPuerExecHarnessOwnedModuleTests` cases (confirmed by
name in `<host>/Temp/UnityPuerExec/editmode_test_results.xml`); the other 21 are
the pre-existing journal/refresh cases, all still green.

> The 29 includes the `CallerFileWithTheEntryPrefixInsideAServerWrittenBaseIsStillRecorded`
> case added with the narrowed fallback described above, so the run covers the
> final rule set, not only the first draft.

### Default mocked suite (documented command line)

```
python -m unittest tests.test_cleanup_validation_host_tool tests.test_cli_version \
  tests.test_default_suite_selection tests.test_direct_exec_client \
  tests.test_editor_log_isolation tests.test_openspec_backlog \
  tests.test_openspec_change_meta tests.test_openspec_spec_hygiene \
  tests.test_package_layout tests.test_preflight_compile_check \
  tests.test_prepare_validation_host_tool tests.test_puerts_version_compat \
  tests.test_real_host_reset tests.test_refresh_change_signal \
  tests.test_unity_log_brief tests.test_unity_puer_session tests.test_unity_session \
  tests.test_unity_session_cli tests.test_unity_session_modules

Ran 884 tests in 111.094s
OK
```

Raw log: `.tmp/ehefs/default-suite-final.log`.

This change adds exactly one case to this suite
(`test_package_layout.test_harness_owned_entry_paths_are_excluded_from_the_staleness_ledger`;
the file went 31 -> 32 `test_` methods). The remaining difference from the 877
recorded by the archived `cover-import-and-reset-jsenv-real-host` change comes from
changes landed since that record, not from this one. The 8 new EditMode cases live
in the separate Unity-side harness counted under `run_editmode_tests.py`, not here.

---

## Task 5.1 — documentation check

`openspec/specs/validation-host-integration/how-to-run.md` grepped for
`stale-module-policy` (no hits), `import-base-url` (no hits), and `import` (only
the unrelated "import-change tracker" reset bullet). The document carries no
statement about stale-module policy or import base URLs that this change could
make incomplete, so it was **not** edited. The behaviour is stated where it
belongs: the two capability specs plus the `cache-staleness-detection` and
`exec-import-support` deltas.

Deliberate scope note: the new real-host cases are **not** added to
`openspec/specs/validation-host-integration/spec.md` here. That spec's
"Real-host validation covers ES module import resolution and explicit JsEnv
reset" requirement belongs to the archived change that created those cases; the
new cases are described by this change's own `exec-import-support` scenario "A
filesystem import base URL preserves JsEnv continuity" and by the durable
`cache-staleness-detection` requirement. `tasks.md` group 5 asks only whether the
how-to-run document became incomplete, and it did not.

## Task 5.2 — strict validation

```
openspec validate exclude-harness-entry-from-staleness --strict
Change 'exclude-harness-entry-from-staleness' is valid
```

Note on how it was run: the globally installed `openspec` launcher broke during this
session (`Cannot find module .../@fission-ai/openspec/bin/openspec.js` — the package
directory under `~/.bun/install/global/node_modules/@fission-ai/` was empty). The
tool was reinstalled at the pinned version in a throwaway `.tmp/openspec-cli/`
(`bun add @fission-ai/openspec@1.14.1`, the same version the global launcher
reported before it broke) and invoked directly:

```
node .tmp/openspec-cli/node_modules/@fission-ai/openspec/bin/openspec.js \
  validate exclude-harness-entry-from-staleness --strict
```

`--all --strict` additionally reports 4 pre-existing long-requirement-text
warnings in `formal-cli-contract`, `import-change-refresh`, `play-mode-control`
and `validation-host-integration`. None is in a spec this change touches (this
change edits only its own delta specs, and the two durable specs are copies of
those deltas until archive), so they are baseline noise, not a regression.

---

## Task 5.4 — closeout finding summary

**No new follow-up work identified.**

Checks behind that statement:

- The `--stale-module-policy error` path is unchanged for caller-owned staleness,
  so the CLI help's promise about protecting JsEnv state is now reachable in
  filesystem-base-URL mode rather than newly broken.
- No payload key, exit code, or CLI surface changed, so no CLI-side follow-up.
- The HTTP `--import-base-url` coverage gap is explicitly out of scope for this
  change (tasks.md, "Workflow follow-up") and is already recorded by the archived
  `cover-import-and-reset-jsenv-real-host` change; not re-raised here.
- No new validation gap was opened: the fix has a failing-then-passing real-host
  case on 2.2.2, a passing control case, both hosts green, and the archived pair
  still discriminating.

Workflow follow-up for the human (not a finding): the change is ready for
`git commit` -> `openspec archive exclude-harness-entry-from-staleness` ->
final `git commit`. None of it has been executed.
