# Design

## Context

See `proposal.md` — Why. Current state and constraints that shape the approach:

- The whole version-specific surface is four references in `Editor/UnityPuerExecServer.cs`: the `jsEnv` field
  declaration (L172), the `CreateScriptEnv` factory (L1596), the `(Backend)Activator.CreateInstance` call
  (L1609) and `new ScriptEnv(backend)` (L1610). Everything else the server calls on the environment —
  `ExecuteModule(string)`, `Tick()`, `Dispose()`, and `!= null` — exists with the same signature on both
  majors, verified by reading `com.tencent.puerts.core` 2.2.2 and 3.0.0 side by side.
- `ILoader` is byte-identical between the two majors (`Runtime/Src/Loader.cs:18-22` in both), so
  `PuerExecLoader` needs no version awareness.
- Both majors put their runtime types in `namespace Puerts`, and both name their runtime assembly definition
  `com.tencent.puerts.core`. The existing asmdef `references` entry therefore works unchanged on both.
- The 3.x factory resolves a concrete `Backend` **by name at runtime** (`Puerts.BackendV8` / `BackendNodeJS` /
  `BackendQuickJS`) because `ScriptEnv` demands an explicit backend and the concrete types live in a separate
  backend assembly this package deliberately does not reference. That reflection, and its "no JavaScript
  backend installed" diagnostic, is already shipped and tested.
- Issue #4 reports that 2.2.2 lacks `ScriptEnv`. That is correct. It also reports 2.2.2 lacks `Backend*`; that
  part is **wrong** — `Runtime/Src/Backend.cs` in 2.2.2 defines `Backend`, `BackendV8`, `BackendNodeJS` and
  `BackendQuickJS`. The only missing type is `ScriptEnv`, which does not change the approach but does mean the
  2.x branch must not be justified by "no Backend type exists".
- `tools/preflight_compile_check.py` parses only `error CS` diagnostics. A C# warning does not fail it, so
  warning noise is not caught by the existing gate — it is caught by a human reading the host log.
- Two hosts are available for evidence: `c3-client-tree2` (branch `tree2`, now at `849a3eb590`,
  `com.tencent.puerts.core` **2.2.2**, Library already imported, no live Editor) and `c3-client-tree5`
  (branch `tree5`, `com.tencent.puerts.core` **3.0.0**, Library imported, no live Editor, carries an
  *embedded* `com.txcombo.unity-puer-exec` 0.12.0 that shadows a `file:` wiring).

## Goals / Non-Goals

**Goals:**

- One published package source that compiles and runs on both majors, with the major resolved from the host
  rather than chosen by an operator.
- Zero behavior change on the 3.x path. It is the shipped, tested path; the risk budget for this change goes
  entirely to 2.x.
- A compile-time selection, not a runtime probe. A runtime type probe would still require both type names to
  appear in the source, which is exactly what fails to compile on 2.x.

**Non-Goals:**

- Supporting PuerTS majors below 2.2.2, or any non-V8/Node/QuickJS backend.
- Changing the CLI, the HTTP protocol, or any response payload. No PuerTS version is reported to callers.
- The `jsEnvs` / `Eval` host-runtime escape hatch from issue #4's side note. It spans both majors and is a
  documentation question; it is tracked as a separate follow-up change.

## Decisions

### D1: `versionDefines` on the Editor asmdef, keyed to the bare floor `3.0.0`, defining `PUERTS_3`

```json
"versionDefines": [
  { "name": "com.tencent.puerts.core", "expression": "3.0.0", "define": "PUERTS_3" }
]
```

Unity sets `PUERTS_3` only when `com.tencent.puerts.core` is present **and** its version satisfies the
expression; the existing `references` entry already makes the package a hard requirement, so "absent" is not a
state this assembly can be compiled in.

*Why a bare version rather than the bracketed `[3.0.0` that issue #4 suggested* — this was settled
empirically, not from documentation, and the first attempt was wrong. A bare version in `versionDefines` means
"this version or higher": `com.unity.cinemachine` gates the same package three times at `5.3.1`, `7.3.1` and
`14.0.0` with three cumulative defines, which only reads as a floor. Bracketed expressions in shipping Unity
packages always carry **both** bounds (`[6000.0.52f1,6000.1.0)`, `[2021.1.2f1,2021.2.0a1]`,
`[6000.3.0a1,7000)`); the one-sided `[3.0.0` appears nowhere. It was tried first and **matched nothing** —
Unity ignored it silently, `PUERTS_3` never reached the response file, and the 3.0.0 host compiled the 2.x
branch, surfacing only as `warning CS0618: 'JsEnv' is obsolete` on three lines of this package. A future 3.x or
4.x host needs no edit under either reading, so the floor costs nothing.

*Why detect 3 rather than detect 2*: the failure directions are asymmetric. If the expression silently fails to
match, `PUERTS_3` is undefined and a 3.x host compiles the 2.x branch — which still compiles, because 3.0.0
keeps `JsEnv` (`Runtime/Src/JsEnv.cs:32`), only `[Obsolete]`. A mis-detection therefore degrades to a visible
CS0618 warning on 3.x, never to a hard failure. The reverse mapping would turn a silent mis-detection on a 2.x
host into CS0246, i.e. the exact bug being fixed. Detecting the newer major puts the soft failure on the newer
host.

*Alternative considered — two package variants or a separate 2.x asmdef*: rejected. It doubles the published
surface, and OpenUPM consumers would have to know which to install.

### D2: `#if PUERTS_3` on the field declaration and the factory only; keep the name `jsEnv`

```csharp
#if PUERTS_3
        private static ScriptEnv jsEnv;
#else
        private static JsEnv jsEnv;
#endif
```

and

```csharp
#if PUERTS_3
        private static readonly string[] JsBackendTypeNames = { ... };
        private static ScriptEnv CreateScriptEnv(ILoader loader) { ...unchanged... }
#else
        private static JsEnv CreateScriptEnv(ILoader loader) => new JsEnv(loader);
#endif
```

`JsBackendTypeNames` moves inside the 3.x branch because on 2.x it would be an unused private field (CS0169
noise in a host log this package otherwise keeps clean). The method keeps its name and its `ILoader` parameter,
so `EnsureJsEnv`, `DisposeJsEnv` and the `/reset-jsenv` path are untouched — and `exec-import-support`'s
requirement language ("disposes the current JsEnv and creates a new one") stays literally true on both majors,
since "JsEnv" there names a role, not the 3.x-deprecated type.

*Alternative considered — an internal `IJsEnvironment` adapter with two implementations*: rejected. It would
wrap three call sites (`ExecuteModule`, `Tick`, `Dispose`) behind a new type in the Editor assembly, add an
allocation and an indirection on the hot `Tick` path, and need its own tests, all to remove two `#if` blocks.
The `#if` blocks are local to the declaration and the factory; no conditional code appears in any request-handling
path.

*Alternative considered — use `JsEnv` on both majors and delete the reflection*: rejected. It would change the
shipped 3.x path (losing the backend-resolution diagnostic that tells an operator "no JavaScript backend
assembly is installed"), knowingly build on a type PuerTS marked `[Obsolete("use ScriptEnv instead")]`, and
break outright the first time PuerTS removes `JsEnv`.

### D3: dependency floor `2.2.2`, not a range

`package.json` declares `"com.tencent.puerts.core": "2.2.2"`. UPM reads a `dependencies` entry as a minimum,
so 3.x hosts keep resolving without change, and `2.2.2` is the version this change actually verifies rather
than a guessed lower bound. `tests/test_package_layout.py` pins that string and is updated in the same commit,
so the floor cannot drift silently.

`openspec/specs/openupm-release-pipeline/spec.md` states the `3.0.0` floor as a durable requirement; the delta
in this change modifies it to `2.2.2` so the spec and the package cannot disagree after archive.

### D4: evidence from two hosts, 2.x first

Order matters because the 2.x host is the one that currently cannot compile at all:

1. `tools/preflight_compile_check.py --project-path <tree2>` → proves no `error CS` on 2.2.2 (the issue's exact
   symptom) and, by absence of CS0618 in that log, that the 2.x branch was taken.
2. `tools/run_editmode_tests.py` against tree2 → the package's own EditMode assembly runs on 2.2.2.
3. Real-host `exec` / `play` against tree2 → the behavioral risk in D5 below.
4. `prepare_validation_host.py --clear-embedded-shadow --project-path <tree5>` then preflight + EditMode on
   tree5 → proves the 3.x path is untouched, including that `PUERTS_3` was in fact defined (a 3.x compile with
   no CS0618 and no CS0246 can only be the `ScriptEnv` branch).

tree5's embedded 0.12.0 copy must be cleared, not left in place: an embedded package shadows the `file:`
wiring, so the tests would silently exercise the old shipped source. `--restore-embedded-shadow` puts it back.

## Risks / Trade-offs

- **[2.x module execution differs]** 2.2.2's `JsEnv` sets `loaderCanCheckESM = loader is IModuleChecker`
  (`Runtime/Src/Default/JsEnv.cs:110`) and `PuerExecLoader` implements only `ILoader`, not `IModuleChecker`. The
  harness specifier is `puer-exec://harness/<requestId>`, which has no file extension for a fallback ESM check
  to read. → Mitigation: this is exactly why `host-validation` is in the change's `evidence`. Real-host `exec`
  on tree2 is a required task, not an optional one, and it covers `--import-base-url` and
  `--reset-jsenv-before-exec` too. If ESM detection does fail on 2.x, the fix is to add `IModuleChecker` to
  `PuerExecLoader` under the same `#if` split — a contained follow-up, not a redesign. Issue #4's reporter
  observed `exec` working end to end on 2.2.2 with the equivalent local workaround, which is corroborating but
  not substituting evidence.
- **[`versionDefines` silently does not match]** This one **happened**, with the one-sided `[3.0.0` form:
  preflight on the 3.0.0 host reported `status: passed`, `exit_code: 0`, `diagnostics: []`, and the assembly
  compiled — through the wrong branch. Nothing this repository gates on failed, because
  `preflight_compile_check.py` parses only `error CS` and the mis-detection produced warnings. It was caught
  solely by reading `UnityPuerExec.Editor.rsp` for the define. → Mitigation, kept as a permanent obligation
  rather than a one-off: a `passed` preflight is **not** evidence that the intended branch compiled. Task 4.2
  requires the define to be present in the 3.x response file and task 3.2 requires it to be absent from the
  2.x one, and D1's asymmetry means the soft direction is the one that gets checked. The pin in
  `tests/test_puerts_version_compat.py` rejects a one-sided bracket expression outright.
- **[Two `#if` branches to maintain]** Every future edit to environment construction has to be correct twice.
  → Mitigation: the branches are confined to the declaration and the factory; no request-handling code is
  conditional, and the shared name `jsEnv` means call sites are written once.
- **[tree2 is now a 2.x host]** The repository's `.env` names tree2 as *the* validation host, and most existing
  real-host evidence was gathered on 3.x there. → Mitigation: the switch is recorded in the change and in
  `backup/tree2-before-puerts2-switch-20261106` (previous tip `1526a93b63`), so the host can be restored with
  one `git reset --hard`. 3.x remains covered by tree5, which already has an imported Library.

## Migration Plan

1. Land the three source edits plus the test pin in one commit; run the mocked default suite.
2. Wire tree2 with `prepare_validation_host.py` (adds a `file:` entry and `testables`) and run the 2.x evidence.
3. Clear tree5's embedded shadow, wire it, run the 3.x evidence, then `--restore-embedded-shadow` and
   `--restore-manifest` to leave tree5 as found.
4. No consumer migration: the dependency is relaxed, never tightened, and no payload changes. Rollback is
   reverting the commit; hosts already on 3.x are unaffected either way.
