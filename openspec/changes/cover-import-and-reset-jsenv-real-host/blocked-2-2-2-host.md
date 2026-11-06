# Blocked on the 2.2.2 host: every shared-device real-host case fails in `setUp`

Discovered while running task 3.1, which needs the two new import-context cases executed
against the 2.2.2 host (`c3-client-tree2`). They cannot run, and neither can any other case
in any shared-device class on that host.

## Symptom

```
AssertionError: shared Editor did not restore the active scene:
  {'status': 'failed',
   'error': 'Error: invalid arguments to GetType or the overload is striped by unity',
   'stack': '... at run (puer-exec://entry/<id>:1:731)'}
```

Raised from `_restore_active_scene` (`tests/test_real_host_integration.py:1102`), called by
`_reset_shared_host_state` (`:1193`) from `setUp` (`:665`). It fires before every case body.

## Not caused by this change

- A pre-existing, unmodified case fails identically:
  `test_exec_globals_are_visible_across_requests_against_real_host` →
  `Ran 1 test ... FAILED (failures=1)`, same `setUp` → `_restore_active_scene` path.
- `git diff` contains no hunk in `_restore_active_scene`, `_reset_shared_host_state`, or `setUp`.

## Root cause

`_restore_active_scene` finds `EditorSceneManager.ClearSceneDirtiness` by looping over
`AppDomain.CurrentDomain.GetAssemblies()` and calling `Assembly.GetType(name)`:

```js
const type = asms.get_Item(i).GetType('UnityEditor.SceneManagement.EditorSceneManager');
if (type) method = type.GetMethod('ClearSceneDirtiness', flags);
```

A direct probe against the live 2.2.2 Editor (`.tmp/reflection_probe.js`) isolates it:

```json
{"appdomain_loaded": true, "asms_ok": true, "asms_length": 222,
 "gettype_found": false,
 "gettype_error": "Error: invalid arguments to GetType or the overload is striped by unity"}
```

`GetAssemblies()` and `get_Item(i)` work. `Assembly.GetType(string)` cannot be bound under
PuerTS 2.2.2 — the overload is stripped, which is exactly what the error says. So `method`
stays `null`, `cleared` stays false, and the helper fails by its own guard. The same call is
reached by every shared-device case, which is why the whole suite is red on this host rather
than a single case.

## Why it was not caught before

`_restore_active_scene` entered the suite in `a205cf3` (2026-10-10, "test(real-host): reset
the shared Editor between cases"). The 2.2.2 host wiring and that host's real-host evidence
come from `support-puerts-2x-jsenv` (archived 2026-11-06) — after that commit. The helper has
therefore never been observed green against a 2.2.2 host; the archived evidence for tree2 was
produced by the scratch probe, not by this suite.

## Why this change does not fix it

Fixing it means replacing a reflection lookup with a binding that PuerTS 2.2.2 supports (for
example `puer.loadType` for the type and a non-generic `GetMethod` overload, or dropping the
`ClearSceneDirtiness` step for hosts that cannot bind it). That is a change to the shared reset
helper's behavior on every host, with its own regression surface across 54 cases and two PuerTS
majors. It is outside "add two cases for `--import-base-url` and `--reset-jsenv-before-exec`",
and absorbing it silently is what the apply skill forbids.

## State of task 3.1

**Not done. Not marked `[x]`.** The two new cases are proven on the 3.0.0 host (task 3.2,
both `ok`), and their 2.2.2 coverage remains unverified because the harness cannot start a
case there. Raise this as a `validation-gap` follow-up candidate at closeout; it blocks the
completion of task 3.1 and therefore the archive of this change.

## Reproduction

```
UNITY_PUER_EXEC_RUN_REAL_HOST_TESTS=1 python -m unittest -v \
  tests.test_real_host_integration.RealHostIntegrationTests.test_exec_globals_are_visible_across_requests_against_real_host
```

Requires a free tree2 host (no interactive Editor holding `Temp/UnityLockfile`). Close a
human-opened Editor with
`python cli/python/unity_puer_exec.py ensure-closed --project-path <tree2>/Project`.
