# Proposal

## Why

GitHub issue #4: on a host with `com.tencent.puerts.core` 2.2.2 the package's Editor assembly does not
compile at all. `UnityPuerExecServer.cs` references `Puerts.ScriptEnv`, which exists only from PuerTS 3.0,
so the host reports CS0246 and the whole control endpoint is unavailable — not degraded, absent. `package.json`
also pins the dependency at `3.0.0`, so a 2.x host cannot even resolve the package. PuerTS 2.x hosts are real
and in active use (the reporter's project, and this repository's own validation host on branch
`devel/v0.1.0-20251226-android`, which ships `com.tencent.puerts.core` 2.2.2).

## What Changes

- The Editor assembly compiles against both `com.tencent.puerts.core` 2.x and 3.x. The PuerTS major version is
  resolved by the assembly definition, not by hand-editing source.
- `Editor/UnityPuerExec.Editor.asmdef` gains a `versionDefines` entry mapping `com.tencent.puerts.core`
  `3.0.0` (meaning "3.0.0 or higher") to the symbol `PUERTS_3`.
- `Editor/UnityPuerExecServer.cs` splits JavaScript-environment construction on `#if PUERTS_3`: 3.x keeps the
  existing reflected-`Backend` + `ScriptEnv` path; 2.x constructs `new JsEnv(loader)`.
- The declared dependency drops from `3.0.0` to `2.2.2`, the lowest version this package supports. UPM reads
  that field as a minimum, so 3.x hosts keep resolving unchanged.
- The unit test that pins the dependency string is updated to the new floor.
- No change to the CLI, the HTTP protocol, or any response payload. Both branches expose the same three
  operations the server already calls (`ExecuteModule(string)`, `Tick()`, `Dispose()`), so nothing downstream
  of environment construction is version-aware.

Out of scope, recorded as a separate follow-up change: the reporter's side note that
`puer.loadType('Puerts.JsEnv').jsEnvs` plus `env.Eval(code)` reaches the host application's own JavaScript
environment. That is a help-text and guidance question spanning both PuerTS majors, not a compile-compatibility
question, and mixing it in here would put two unrelated contracts in one change.

## Capabilities

### New Capabilities

- `puerts-version-compatibility`: the durable contract for which `com.tencent.puerts.core` major versions the
  package supports, how the active major is detected at compile time, and how the JavaScript environment is
  constructed under each.

### Modified Capabilities

- `openupm-release-pipeline`: the package.json metadata requirement currently mandates
  `com.tencent.puerts.core` at minimum version `3.0.0`. It becomes `2.2.2`, matching the floor this change
  establishes and verifies.

## Impact

- Code: `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`,
  `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExec.Editor.asmdef`,
  `packages/com.txcombo.unity-puer-exec/package.json`.
- Tests: `tests/test_package_layout.py` (dependency pin); package EditMode tests must keep passing on the 3.x
  path; real-host validation runs against a 2.2.2 host.
- Validation host: `F:\C3\unity-puer-exec-workspace\c3-client-tree2` (branch `tree2`, now at
  `849a3eb590`, `com.tencent.puerts.core` 2.2.2) becomes the 2.x host. The 3.x path stays covered by
  `F:\C3\c3-client-tree3` (branch `tree3`, `com.tencent.puerts.core` 3.0.0), which already runs an Editor with
  `-unityPuerExecControl`.
- Published package: the OpenUPM `upm` branch carries the relaxed dependency, widening the set of hosts that can
  install the package. No consumer needs to change.
