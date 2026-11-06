# Real-host evidence (B tasks 3.1–3.4, 4.1–4.4)

Change: `surface-package-warnings-in-preflight`.
Groups 1–2 (tool code + unit tests) were implemented separately; see
`apply-notes-groups-1-2.md`. This file records the real-host proof.

---

## 3.1 — 2.2.2 host (c3-client-tree2): passed, no package warnings

```
python tools/preflight_compile_check.py
```

```json
{
  "status": "passed",
  "kind": null,
  "reason": null,
  "exit_code": 0,
  "diagnostics": [],
  "package_warnings": [],
  "keys": ["diagnostics", "exit_code", "kind", "log_path", "package_warnings",
           "project_path", "reason", "status", "unity_exe_path"]
}
```

Took 44 s. This is the whole point of the task: the current tree is clean, so turning the
gate on **must not change the answer** — and it does not. Same `status: passed` the
pre-change tool reported, now with the additive key present and empty.

Host: `c3-client-tree2/Project`, `com.tencent.puerts.core` 2.2.2, wired by `file:`
dependency (`prepare_validation_host.py --dry-run` → `status: unchanged`,
`embedded_package_shadowing: false`).

## 3.2 — 3.0.0 host (c3-client-tree5): passed, no package warnings

Procedure (repository-owned operations only, per the how-to-run contract):

1. `prepare_validation_host.py --clear-embedded-shadow` → `status: cleared`, moved
   `Project/Packages/com.txcombo.unity-puer-exec` to
   `.unity-puer-exec-embedded-backup/com.txcombo.unity-puer-exec-20261106/`;
   `embedded_package_shadowing: false`.
2. `prepare_validation_host.py` → `status: updated`,
   `dependency: file:../../../unity-puer-exec-workspace/unity-puer-exec/packages/com.txcombo.unity-puer-exec`,
   `package_testable: true`.
3. Preflight.

```json
{
  "status": "passed",
  "kind": null,
  "reason": null,
  "exit_code": 0,
  "diagnostics": [],
  "package_warnings": []
}
```

Took 60 s (first compile of the newly wired package). Host: `c3-client-tree5/Project`,
`com.tencent.puerts.core` 3.0.0.

Restored afterwards: `--restore-embedded-shadow` → `status: restored`;
`--restore-manifest` → `status: restored`, `left_in_place: []`;
`git -C F:/C3/c3-client-tree5 status --short` → **empty**.

## 3.3 — replaying the motivating defect: now fails, naming CS0618

The defect from `support-puerts-2x-jsenv` was reproduced by changing the Editor asmdef's
`versionDefines` expression from the correct bare floor `"3.0.0"` back to the one-sided
`"[3.0.0"` — the form that matches nothing, so the 3.0.0 host compiles the 2.x branch:

```json
[{"name": "com.tencent.puerts.core", "expression": "[3.0.0", "define": "PUERTS_3"}]
```

Preflight against the 3.0.0 host:

```json
{
  "status": "failed",
  "kind": "package_deprecation",
  "reason": "package compile preflight reported 6 package deprecation diagnostic(s) (CS0618, CS0619)",
  "exit_code": 0,
  "diagnostics": [],
  "package_warnings": [
    {"code": "CS0618", "file": ".../packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs", "line": 1654, "column": 24, "message": "'JsEnv' is obsolete: 'use ScriptEnv instead'"},
    {"code": "CS0618", "file": "...", "line": 188,  "column": 24, "message": "'JsEnv' is obsolete: 'use ScriptEnv instead'"},
    {"code": "CS0618", "file": "...", "line": 1656, "column": 24, "message": "'JsEnv' is obsolete: 'use ScriptEnv instead'"},
    ... (the same three lines repeated)
  ]
}
```

**This is the answer the change exists to produce.** `exit_code: 0` is the silent half —
the assembly compiled — and `status: failed` with `kind: package_deprecation` is the new
half. Pre-change, this exact log yielded `{"status": "passed", "diagnostics": []}`.

### Two details, both load-bearing

- **6 entries, 3 distinct source lines.** Unity's own batch log writes each package warning
  twice: `grep -c CS0618` finds 10 occurrences, and
  `grep -o 'UnityPuerExecServer\.cs([0-9]*,[0-9]*): *warning CS0618' | sort | uniq -c`
  yields exactly 2 each for lines 1654, 1656, and 188. The parser reports what the log says;
  deduplication would be a separate decision, and the `reason` counts diagnostics.
- **The host's own deprecation warnings were correctly excluded.** The same log carries
  `Assets/Res/.../CorridorLamp.cs(29,4): warning CS0618: 'ParticleSystem.enableEmission' is
  obsolete` (and more), and none of them appear in `package_warnings`. This is the
  attribution rule doing its job on a real mixed log, which is what spec scenario
  "A host warning outside this package does not fail the run" requires.

The asmdef was reverted and verified byte-identical to its original content
(SHA-256 `cdccadc9…06e63`, blob hash equal to `HEAD`, `git diff --quiet` exit 0), so the
defect is not present in the tree. Note for anyone repeating this: the file is LF in the
working tree while `core.autocrlf=true`, so a Python text-mode write, or `git checkout`
after such a write, round-trips it to CRLF and leaves a phantom ` M` in `git status`.
Restore with an explicit `write_bytes` of the LF form, or `git add` + `git reset` to
refresh the stat cache.

## 3.4 — the real-host suite inherits the behavior

- **One code path.** `_SharedRealHostDevice.setUpClass` calls
  `preflight_compile_check.require_preflight(cls.project_path, cls.unity_exe_path)`
  (`tests/test_real_host_integration.py:624`), **before** `_start_shared_host` on the next
  lines. There is no second, suite-local compile check.
- **Before the interactive launch.** `_ensure_clean_test_boundary` runs, then the preflight,
  then `cls._shared_host = _start_shared_host(...)`. A deprecation failure raises
  `AssertionError(format_failure_detail(result))` from inside `require_preflight`, i.e. in
  `setUpClass`, so the class is never launched.
- **Unit-proven at that entry point.**
  `test_require_preflight_raises_the_deprecation_detail` asserts `require_preflight` raises
  the rendered deprecation detail; `require_preflight` raises on any `STATUS_FAILED`, which
  now includes `KIND_PACKAGE_DEPRECATION`.
- **Observed indirectly, and that is expected.** Neither task 3.1 nor 3.2 exercised a real
  suite run that fails preflight, because a failing real-host run is not something to stage
  against a host under validation. The ordering above is the claim, and it is a one-line
  inspection rather than an inference.

## 3.1/3.2 additivity check on real payloads

Both real payloads above carry all nine keys, matching every code path exercised in
`.tmp/preflight_payload_keys.py` (passed / skipped / compile_failure / launch_failure /
package_deprecation / package_warning). Nothing was reshaped.

---

## 4.1 — documentation matches the emitted payload

`openspec/specs/validation-host-integration/how-to-run.md` now names `package_warnings`, the
deprecation failure, and `--strict-package-warnings`, with a table of all nine keys.

Verified by deriving the key set from every `run_preflight` return path and comparing it
against the keys parsed out of the documented table (`.tmp/preflight_payload_keys.py`):

```
emitted    : diagnostics, exit_code, kind, log_path, package_warnings, project_path, reason, status, unity_exe_path
documented : diagnostics, exit_code, kind, log_path, package_warnings, project_path, reason, status, unity_exe_path
missing from doc: []
documented but not emitted: []
MATCH
```

Per-entry keys (`code`, `message`, `file`, `line`, `column`) are documented and emitted too.

## 4.2 — mocked default suite

```
python -m unittest <the documented default-suite command line>
Ran 877 tests in 62.561s
OK
```

## 4.3 — strict validation

```
openspec validate surface-package-warnings-in-preflight --strict
Change 'surface-package-warnings-in-preflight' is valid
```

## 4.4 — closeout finding summary

**New follow-up candidates identified.**

1. **`tooling-improvement` — the same attribution rule belongs in
   `tools/run_editmode_tests.py`.** That runner reads its own batch log and, like the old
   preflight, only looks for `error CS`. A package compiled against a retired API would pass
   it the same way. The proposal's "Workflow follow-up" already names this; it is confirmed,
   not speculative, because the defect replay in task 3.3 proves the log shape occurs in a
   normal package compile.
2. **`tooling-improvement` — Unity writes each package warning into the batch log twice.**
   `package_warnings` and `reason` therefore report 6 for 3 source lines. Reporting the
   duplicate count is faithful to the log but reads as noise to a human; a dedupe decision
   (or a documented note) is worth making deliberately rather than by accident.
