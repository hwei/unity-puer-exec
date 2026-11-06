# Real-host evidence: import context cases (C tasks 3.1–3.3)

Cases added to `tests/test_real_host_integration.py` (class `RealHostIntegrationTests`):

- `test_exec_resolves_relative_import_through_import_base_url_against_real_host`
- `test_reset_jsenv_before_exec_clears_globals_with_an_unchanged_module_against_real_host`

Suite shape went from **52 → 54** cases; `RealHostIntegrationTests` from **27 → 29**.

---

## 3.1 — 2.2.2 host (c3-client-tree2)

**Both new cases pass**, once the shared reset helper was repaired (see the addendum below).

```
test_exec_resolves_relative_import_through_import_base_url_against_real_host ... ok
test_reset_jsenv_before_exec_clears_globals_with_an_unchanged_module_against_real_host ... ok
Ran 2 tests in 137.446s
OK
```

Host: `c3-client-tree2/Project`, `com.tencent.puerts.core` 2.2.2, wired by a `file:`
dependency (`prepare_validation_host.py --dry-run` → `status: unchanged`,
`embedded_package_shadowing: false`).

This is the answer the change was created for: the surface `support-puerts-2x-jsenv`
hand-drove in a gitignored scratch probe is now covered by committed cases, on the host
where the PuerTS major is the one that could diverge (`PuerTS 2.2.2` gates ESM detection on
`loader is IModuleChecker`, and `PuerExecLoader` implements only `ILoader`).

Launch cost on this host: 1 interactive launch + 1 batch preflight, and no validation-temp
residue afterwards.

### Addendum: the host blocker was fixed, so 3.1 is no longer blocked

The first attempt at 3.1 could not run: every shared-device case on this host failed in
`setUp` at `_restore_active_scene` with `invalid arguments to GetType or the overload is
striped by unity`. That was a pre-existing harness defect (`Assembly.GetType(string)` does
not bind under PuerTS 2.2.2), documented in `blocked-2-2-2-host.md` because it was outside
this change's scope at the time.

On review the human asked for it to be fixed. `_restore_active_scene` now resolves the
`System.Type` by scanning each loaded assembly's `GetTypes()` for a matching `FullName`
instead of calling `Assembly.GetType(string)`. `GetTypes()`, `get_Item`, `FullName`, and
`GetMethod` are plain reflection and bind on both PuerTS majors.

Probed on 2.2.2 before changing anything (`.tmp/type_access_probe.js`):

```json
{"asms": 222, "D_gettypes_found": true, "D_assemblies_scanned": 72,
 "D_getmethod": true, "D_invoke": "ok",
 "B_3arg_err": "c# exception:Could not load type ... from assembly 'System.Private.CoreLib'"}
```

Note the `B_3arg_err`: the 3-argument `GetType(string, bool, bool)` *does* bind, but is
resolved against every assembly including `System.Private.CoreLib`, so it throws rather
than returning null. The `GetTypes()` walk avoids both problems.

The regression check is that a pre-existing case which previously failed in `setUp` now
passes on this host:

```
test_exec_globals_are_visible_across_requests_against_real_host ... ok
Ran 1 test in 86.895s
OK
```

`blocked-2-2-2-host.md` is retained as the record of the defect and its diagnosis; it is no
longer a live blocker.

---

## 3.2 — 3.0.0 host (c3-client-tree5)

Procedure: `--clear-embedded-shadow` (report `status: cleared`, one directory moved to
`.unity-puer-exec-embedded-backup/`), `prepare_validation_host.py` (report `status: updated`,
`embedded_package_shadowing: false`, `package_testable: true`), run, then restore.

```
python .tmp/run_real_host_counting.py "F:/C3/c3-client-tree5/Project" \
  .tmp/host-evidence/c32-tree5-launches.json \
  <both new cases>

test_exec_resolves_relative_import_through_import_base_url_against_real_host ... ok
test_reset_jsenv_before_exec_clears_globals_with_an_unchanged_module_against_real_host ... ok
Ran 2 tests in 133.473s
OK
```

### Host state after restore

```
git -C F:/C3/c3-client-tree5 status --short     -> (empty)
Project/.unity-puer-exec-*                      -> no such directory (backups removed)
Project/Packages/com.txcombo.unity-puer-exec/   -> restored, package.json version 0.12.0
```

---

## 3.3 — Editor launch count unchanged from the 1.1 baseline

Measured by polling `Unity.exe` pids and the host's published endpoint while the suite ran
(`.tmp/run_real_host_counting.py`); the poller counts a published pid only when that pid is
also a live Unity process, so a stale `endpoint.json` left by an earlier run cannot inflate it.

```json
{
  "exit_code": 0,
  "unity_pids_before": [],
  "new_unity_pids_during_run": [78700, 91704],
  "endpoint_unity_pids_seen": [91704],
  "interactive_launch_count": 1,
  "batch_preflight_launches": 1
}
```

| | Baseline (1.1) | With the 2 new cases |
|---|---|---|
| Cases | 52 | 54 |
| Interactive Editor launches | 1 per class | **1** for `RealHostIntegrationTests` |
| Batch preflight launches | 1 per suite invocation | **1** |

Both new cases are ordinary members of the existing shared-device class, so they add two
exec round-trips against an already-running Editor and no launch. The
cost-scales-with-cases-not-relaunches requirement holds.

### One earlier measurement was discarded, and why

A first run of the same two cases reported `interactive_launch_count: 2` with
`unity_pids_before: []` and `endpoint_unity_pids_seen: [4600, 67416]`. pid `4600` was not
among the processes started during that run — it was a stale `endpoint.json` record left by
the previous invocation whose Editor had already exited. The poller was corrected to require
a published pid to be live; the re-run above is the recorded evidence. Ordering the pid
numbers against `new_unity_pids_during_run` is what exposes the artifact.

---

## 3.4 — mocked default suite

```
python -m unittest tests.test_real_host_reset
Ran 22 tests in 0.768s
OK
```

Full documented default suite: `Ran 877 tests in 62.561s`, `OK`.

---

## A finding worth keeping: `--import-base-url` defeats `ctx.globals` continuity

The reset case was first written with a filesystem `--import-base-url` fixture, reusing the
import case's module directory. It failed on the 3.0.0 host at the *baseline* step, and the
payload named the mechanism:

```json
"recovery": {"performed": true, "type": "jsenv_reset", "reason": "module_cache_stale",
             "policy": "auto-reset",
             "affected_modules": [".../import_fixture~/__puer_exec_entry_5e6d7f66....js"]}
```

`UnityPuerExecProtocol.BuildEntrySpecifier` names the entry module after the request id, so
each exec with a filesystem base URL **writes a new entry file and sweeps the previous one**.
`CheckModuleStaleness` then reports that entry as a changed local module on every exec, the
default `auto-reset` policy resets the JsEnv every time, and `ctx.globals` can never survive
across execs. The case was rewritten to use inline code only, where no local module is
registered and "no module changed" holds trivially.

This is a product-behavior interaction, not a test convenience: **with a filesystem
`--import-base-url`, `ctx.globals`, module singletons, and any other JsEnv-scoped state do not
survive between execs.** That is worth a follow-up candidate at closeout (it is the same
survival property the CLI help advertises `--stale-module-policy error` to protect).
