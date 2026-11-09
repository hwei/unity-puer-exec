# Proposal

## Why

A filesystem `--import-base-url` silently defeats JsEnv state continuity. The
server writes its own per-request entry module into the import base directory —
`UnityPuerExecProtocol.BuildEntrySpecifier` names it
`__puer_exec_entry_<request-id>.js`, so the name differs on every request — and
`StartJobEvaluation` deletes the previous one. `PuerExecLoader.GetModuleContent`
then reads that file like any other local module and calls
`RecordLocalModuleRead`, which records an mtime fingerprint. By the next exec the
file is gone, so `CheckModuleStaleness` reports it stale, and the default
`auto-reset` policy performs a server-owned `ResetJsEnv` before every single
exec.

The consequence is that `ctx.globals`, module singletons, and any other
JsEnv-scoped state cannot survive across execs whenever a filesystem
`--import-base-url` is in use. This was found while writing a real-host test:
seeding `ctx.globals` and reading it back on the next exec returned `null`, and
the payload named the cause itself —

```json
"recovery": {"performed": true, "reason": "module_cache_stale",
             "affected_modules": [".../import_fixture~/__puer_exec_entry_5e6d7f66....js"],
             "policy": "auto-reset"}
```

That is a false positive with a real cost. The CLI help advertises
`--stale-module-policy error` as the way to protect `ctx.globals` and module
singleton continuity, but with a filesystem base URL that protection is
unreachable: the caller is told a module changed when the only change was the
harness's own scratch entry file, and the run is either rejected with
`module_cache_stale` or silently reset. The tool reports a state change it
caused itself.

## What Changes

- The server records which local modules it generated for the current
  invocation (the per-request entry file it wrote into a filesystem
  `--import-base-url` directory) and excludes those from the staleness ledger.
  A file the harness wrote is not a module the caller changed.
- Staleness detection for **every other** local module is unchanged: a caller's
  module whose mtime moved is still stale, and a caller's module that was
  **deleted** is still stale. The existing `cache-staleness-detection`
  requirement "Removed loaded module is stale" is preserved exactly as written.
- The exclusions are scoped and cleaned up with the entry file itself, so a
  deleted temporary entry cannot leave a permanent hole in the ledger.

## Why not the alternative

The obvious one-line fix is to stop treating `!File.Exists(...)` as stale. That
is rejected: it would delete the durable requirement "Removed loaded module is
stale", turning a harness false positive into a silent user-facing false
negative — a caller who deletes an imported module would no longer get recovery,
and would see only a downstream module-resolution failure. The defect is that
the harness's own scratch file is in the ledger at all, so the fix belongs in
what gets recorded, not in what counts as stale.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `cache-staleness-detection`: the ledger's contents are amended — modules the
  server generated for its own request framing are not tracked — while the
  existing staleness rules for caller-owned modules are restated as unchanged.
- `exec-import-support`: "Staleness detection is the entry-point guard; reset is
  the remedy" gains the requirement that a filesystem `--import-base-url` does
  not itself cause a reset, so its promise that callers can retain JsEnv
  continuity holds in that mode too.

## Impact

- Package: `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs` —
  a harness-owned path set maintained alongside `PendingTempEntryPaths`, a guard
  in `RecordLocalModuleRead`, and cleanup on the existing
  `CleanupTempEntryFile`/`SweepPendingTempEntryFiles` paths.
- Tests: mocked coverage for the ledger decision (a harness-owned path is not
  tracked; a caller path still is), plus a real-host case proving `ctx.globals`
  survives across execs **with** a filesystem `--import-base-url`.
- Specs: `cache-staleness-detection` and `exec-import-support` deltas.
- No CLI surface change, no payload key change, no exit-code change. Callers see
  fewer spurious `recovery` blocks and, under `--stale-module-policy error`,
  fewer spurious `module_cache_stale` rejections.
- Both PuerTS majors are affected equally, because the defect is in this
  package's ledger bookkeeping rather than in a version-gated branch; validation
  still runs against both.
- Follow-up from `cover-import-and-reset-jsenv-real-host` (archived
  `2026-11-09`), whose `validation-evidence.md` and `apply-notes-2-4-and-4-1.md`
  record the observed payload and why the test was rewritten to inline code.
