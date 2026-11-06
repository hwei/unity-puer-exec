# Validation evidence — support-puerts-2x-jsenv

Every number below was produced against the **final** source revision, including the
comment that documents the `versionDefines` trap. Two runs earlier in the session were made
against intermediate revisions and are not cited; where one of them mattered, it is called
out in the "Finding" section, because it is the reason the trap is documented in source.

## Hosts

| role | path | branch / commit | `com.tencent.puerts.core` | Editor |
|---|---|---|---|---|
| 2.x | `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project` | `tree2` @ `849a3eb590` (= `devel/v0.1.0-20251226-android`) | **2.2.2** | 2022.3.62f2 |
| 3.x | `F:\C3\c3-client-tree5\Project` | `tree5` @ `3c881f2b6f` | **3.0.0** | 2022.3.62f2 |

tree2 was reset to that commit specifically to obtain a 2.2.2 environment; its previous tip
`1526a93b63` is preserved on `backup/tree2-before-puerts2-switch-20261106`. The switch
removed the branch's previously git-tracked embedded copy of this package, as intended. On
2.2.2 there is no `com.tencent.puerts.v8` package: the native backend ships inside
`Packages/com.tencent.puerts.core/Plugins/x86_64/puerts.dll`.

tree5 carried an **embedded, git-tracked** `com.txcombo.unity-puer-exec` 0.12.0, which shadows
a `file:` wiring. It was moved with `prepare_validation_host.py --clear-embedded-shadow`
(to `Project/.unity-puer-exec-embedded-backup/com.txcombo.unity-puer-exec-20261106/`) before
any 3.x number was taken, so none of the 3.x evidence below describes the old shipped source.

Both hosts were wired by `prepare_validation_host.py`: `"status": "updated"`,
`"embedded_package_shadowing": false`, dependency
`file:../../../unity-puer-exec-workspace/unity-puer-exec/packages/com.txcombo.unity-puer-exec`,
package listed under `testables`.

## Finding: a one-sided `versionDefines` expression matches nothing, silently

The first implementation used `"expression": "[3.0.0"`, the form issue #4 suggested. On the
3.0.0 host, `preflight_compile_check.py` reported:

```json
{"status": "passed", "kind": null, "reason": null, "exit_code": 0, "diagnostics": []}
```

and the assembly compiled — **through the 2.x branch**. `PUERTS_3` never reached
`UnityPuerExec.Editor.rsp`, so the `#else` arm was selected on a 3.x host, producing:

```
UnityPuerExecServer.cs(181,24):   warning CS0618: 'JsEnv' is obsolete: 'use ScriptEnv instead'
UnityPuerExecServer.cs(1647,24):  warning CS0618: 'JsEnv' is obsolete: 'use ScriptEnv instead'
UnityPuerExecServer.cs(1649,24):  warning CS0618: 'JsEnv' is obsolete: 'use ScriptEnv instead'
```

Nothing this repository gates on failed. `preflight_compile_check.py` parses only `error CS`
diagnostics, so a wrong-branch compile that still compiles is invisible to it. The defect was
caught solely by reading the response file for the define — which is why tasks 3.2 and 4.2
require the response-file check in both directions, and why `design.md` (D1, Risks) now
records that a `passed` preflight is not evidence that the intended branch compiled.

The fix is a **bare** version floor, `"expression": "3.0.0"`, which Unity reads as "3.0.0 or
higher". That reading is not taken from documentation but from shipping Unity packages in
this host's own `Library/PackageCache`: `com.unity.cinemachine` gates the same package three
times at `5.3.1`, `7.3.1` and `14.0.0` with three cumulative defines, which only makes sense
as a floor, and every bracketed expression found there carries both bounds
(`[6000.0.52f1,6000.1.0)`, `[2021.1.2f1,2021.2.0a1]`, `[6000.3.0a1,7000)`). The one-sided
form appears nowhere. `tests/test_puerts_version_compat.py` now rejects a leading `[`.

The direction of the mapping is what kept this a warning instead of a break: detecting the
*newer* major means a mis-detection lands on a 3.x host, where `JsEnv` still exists and is
merely `[Obsolete]`. Had the define keyed on 2.x instead, the same silent mismatch would have
produced CS0246 on a 2.x host — issue #4 itself.

## Mocked layer (no Editor)

| check | result |
|---|---|
| default suite, the documented command line, now including `tests.test_puerts_version_compat` | `Ran 846 tests in 76.689s` — `OK`, exit 0 |
| `tests.test_puerts_version_compat` alone | 12/12 |
| `tests.test_package_layout` alone | 31/31 |
| guard-teeth probe `.tmp/puerts_compat_guard_teeth.py` | 4 of 4 mutants caught |

The mutants, each written to a scratch copy with the test module repointed at it: removing
the field's `#if`/`#else` (2 failures); removing the factory's `#if` so `ScriptEnv`/`Backend`
become unconditional (3 failures); emptying `versionDefines` (2 failures); and setting the
expression to the one-sided `[3.0.0` (1 failure). The last one is the defect above, pinned as
a regression.

## Compile preflight — the branch selection is asserted, not assumed

`python tools/preflight_compile_check.py` returned `{"status": "passed", "exit_code": 0,
"diagnostics": []}` on both hosts. That JSON is identical for a correct compile and for the
wrong-branch compile above, so the logs and response files were read directly.

| probe | 2.x host (tree2, 2.2.2) | 3.x host (tree5, 3.0.0) |
|---|---|---|
| `status` / `exit_code` / `diagnostics` | `passed` / `0` / `[]` | `passed` / `0` / `[]` |
| `grep -c "error CS"` over the whole batch log | `0` | `0` |
| `Csc .../UnityPuerExec.Editor.dll` in the log (a real compile, not a Bee short-circuit) | `2` | `2` |
| `UnityPuerExecServer.cs` present in `UnityPuerExec.Editor.rsp` | yes | yes |
| **`PUERTS_3` in `UnityPuerExec.Editor.rsp`** | **`0` — 2.x branch** | **`1` — 3.x branch** |
| PuerTS reference in the rsp | `com.tencent.puerts.core.ref.dll` | `com.tencent.puerts.core.ref.dll` |
| any `warning CS` naming this package | none | none |

Issue #4's symptom — `error CS0246` on `ScriptEnv` at the field declaration and at
`CreateScriptEnv` — is absent on the 2.2.2 host, and the absence of `CS0618` on the 3.0.0
host is the positive proof that it took the `ScriptEnv` path rather than the deprecated one.

An intermediate tree2 run had to be discarded: Bee found the assembly up to date and emitted
no `Csc` line, so its `passed` described the previous revision. The `Csc` count is now part
of the task's verification for that reason.

## Package EditMode assembly

`python tools/run_editmode_tests.py`:

| host | status | total | passed | failed | skipped |
|---|---|---|---|---|---|
| tree2 (2.2.2) | `passed`, exit 0 | 21 | 21 | 0 | 0 |
| tree5 (3.0.0) | `passed`, exit 0 | 21 | 21 | 0 | 0 |

21 matches the pre-change 3.x baseline, so the assembly was discovered and run on 2.2.2
rather than silently skipped — `run_editmode_tests.py` reports an assembly Unity did not
compile as `no_tests_discovered`, not as `passed`.

## End to end against live Editors

Probe `.tmp/puerts2_e2e_probe.py`, driving the real CLI in-process against each host.
Summaries: `.tmp/puerts2-e2e/2-2-2-summary.json`, `.tmp/puerts2-e2e/3-0-0-summary.json`.
The first `exec` cold-launches the Editor; the rest run against the live session.

| step | 2.2.2 (tree2) | 3.0.0 (tree5) |
|---|---|---|
| `exec --code` inline body | exit 0, 44.7 s, `completed`, `{"sum": 2, "rid": "e95fde71c38c46e5b02b9d598ac81f27"}` | exit 0, 52.5 s, `completed`, `{"sum": 2, "rid": "deaa0309b295484687271633b1efbfb2"}` |
| `exec --import-base-url <dir>` with `import greeting from './greeting.js'` | exit 0, 1.7 s, `{"greeting": "first"}` | exit 0, 2.9 s, `{"greeting": "first"}` |
| module rewritten, then `exec --reset-jsenv-before-exec` | exit 0, 2.3 s, `{"greeting": "second-after-reset"}` | exit 0, 3.3 s, `{"greeting": "second-after-reset"}` |
| `play` | exit 0, 3.6 s, `play_state: playing` | exit 0, 4.6 s, `play_state: playing` |
| `stop` | exit 0, 3.3 s, `play_state: edit` | exit 0, 4.1 s, `play_state: edit` |
| | **5 of 5** | **5 of 5** |

The repository's real-host suite has no case for `--import-base-url` or
`--reset-jsenv-before-exec`, so those two were driven by hand on purpose: they are the exact
surface the design's open risk named. Identical payloads on both majors is also the evidence
for the `puerts-version-compatibility` requirement that CLI-observable behavior does not
vary with the host's PuerTS major — same `status`, same `operation`, same `result` shape, and
no version field in either response.

Incidentally exercised on the 2.x host: `ensure-closed` returned exit 0 with
`{"status": "stopped", "closed_via": "graceful"}`, so the graceful-quit path works against a
2.2.2 environment too.

## The design's open risk did not materialize

`design.md` (Risks) flagged that 2.2.2's `JsEnv` sets `loaderCanCheckESM = loader is
IModuleChecker` (`Runtime/Src/Default/JsEnv.cs:110`) while `PuerExecLoader` implements only
`ILoader`, and that the harness specifier `puer-exec://harness/<request-id>` carries no
extension for a fallback ESM check to read. Steps 2 and 3 above are the disproof on 2.2.2: a
relative ESM import resolved through `--import-base-url`, and a rewritten module was picked
up after an explicit reset rather than served from cache.

No `IModuleChecker` was added to `PuerExecLoader`, and task 3.5's conditional branch was not
taken. Both PuerTS majors are served by the same `ILoader`-only loader.

## Host state left behind

- **tree5**: fully restored. `--restore-manifest` and `--restore-embedded-shadow` both
  reported `"status": "restored"`, the embedded 0.12.0 is back at
  `Project/Packages/com.txcombo.unity-puer-exec`, no `file:` entry remains in its manifest,
  both backup directories are gone, and `git -C F:/C3/c3-client-tree5 status --short` is
  empty — the same state it was found in.
- **tree2**: left wired to the development package and left with a live Editor, since
  `./.env` names it as the repository's validation host and further 2.x work continues
  against it. Its `manifest.json` and `packages-lock.json` are dirty as a result;
  `python tools/prepare_validation_host.py --restore-manifest` returns them.
