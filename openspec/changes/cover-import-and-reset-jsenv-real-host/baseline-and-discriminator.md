# Real-host coverage baseline (tasks 1.1 and 1.2)

Recorded before any case was added, so task 3.3 has a fixed number to compare against.

## 1.1 Suite shape

Source: `tests/test_real_host_integration.py` at commit `a7c55f6`.

`grep -c "    def test_" tests/test_real_host_integration.py` → **52**

Cases per class:

| Class | Cases | Shares the host device | Own-boundary cases |
|---|---|---|---|
| `RealHostIntegrationTests` | 27 | yes (`_SharedRealHostDevice`) | 5 (`_OWN_BOUNDARY_INTEGRATION_TESTS`) |
| `RefreshOnChangeRealHostTests` | 13 | yes | 0 |
| `PlayModeCompileBlockRealHostTests` | 7 | yes | 0 |
| `PlayModeRunInBackgroundPersistenceRealHostTests` | 3 | yes | 3 (`stop`) |
| `EditorCrashSurfaceRealHostTests` | 2 | yes | 2 (`stop`) |
| **Total** | **52** | **5 classes** | **10** |

### Editor launch count for a full run

`_SharedRealHostDevice.setUpClass` brings the Editor up once per class and
`tearDownClass` stops it once, so a full run costs:

- **5 interactive Editor launches** — one per shared-device class. Independent of case
  count: `setUpClass` runs once per class no matter how many cases it holds.
- **1 batch-mode preflight launch** — `preflight_compile_check.require_preflight` is
  called from `setUpClass` but caches its result for the process
  (`run_preflight_once` / `_PREFLIGHT_RESULT`), so five classes still cost one batch
  launch per suite invocation.
- Plus per-case launches owned by the 10 own-boundary cases, which stop and
  re-establish the host as their own precondition. Those are a property of those
  cases, not of the class case count.

**Baseline for task 3.3: 5 shared-host interactive launches, 1 preflight batch launch.**

Adding the two new cases to `RealHostIntegrationTests` must leave both numbers at 5 and
1, because they are class-level and the new cases are ordinary (not own-boundary) cases.

## 1.2 The observable that discriminates the explicit flag

### What the default already does

`UnityPuerExecServer.TryAcceptExecRequest` (~line 1477) decides a reset from two inputs:

```csharp
staleModules = CheckModuleStaleness();
var shouldReset = request.reset_jsenv_before_exec ||
    (staleModules.Count > 0 && request.stale_module_policy == "auto-reset");
...
var recoveryReason = request.reset_jsenv_before_exec
    ? "explicit_request"
    : (shouldReset ? "module_cache_stale" : "");
```

`UnityPuerExecJobState` sets `RecoveryPerformed = !string.IsNullOrEmpty(recoveryReason)`,
and `HandleExecAsync` (~line 873) acts on it:

```csharp
if (execJob.RecoveryPerformed) { ResetJsEnv(); }
```

`ResetJsEnv()` = `DisposeJsEnv()` then `EnsureJsEnv()`. `DisposeJsEnv` disposes the
`JsEnv`, clears `LocalModuleFingerprints`, and nulls `jsEnv` and `execLoader`, so the
next `EnsureJsEnv` builds a **fresh engine instance**.

So the default path already resets — but only when `CheckModuleStaleness()` reports a
changed module. That is the behavior task 1.2 must not be confused with.

### The discriminator

With an **unchanged** module and no staleness, `staleModules.Count == 0`, so:

| | `reset_jsenv_before_exec` false | `reset_jsenv_before_exec` true |
|---|---|---|
| `shouldReset` | false | true |
| `recoveryReason` | `""` | `"explicit_request"` |
| `RecoveryPerformed` | false | true |
| `ResetJsEnv()` called | **no** | **yes** |

Two observables follow, and the case asserts both:

1. **`ctx.globals` continuity** — the observable the proposal names.
   `UnityPuerExecProtocol.BuildWrappedScript` backs `ctx.globals` with a process-global:

   ```js
   const __globals = globalThis.__unityPuerExecGlobals || (globalThis.__unityPuerExecGlobals = {});
   const __ctx = Object.freeze({ request_id: __jobId, globals: __globals, args: __args });
   ```

   A marker written to `ctx.globals` in one exec therefore survives every later exec
   **inside the same JsEnv** and is destroyed by a `ResetJsEnv`, because the fresh engine
   has a fresh `globalThis`. `test_exec_globals_are_visible_across_requests_against_real_host`
   already proves the survival half (counter reaches 2 with no flag). The new case is its
   mirror: with the flag, the marker must be **gone**. If `--reset-jsenv-before-exec` were
   a no-op, the marker would survive and the case would fail. That is the discrimination.

2. **`recovery.reason`** — machine-readable, so the case does not depend on inference.
   `BuildRecoveryJson` emits the block only when `RecoveryPerformed`, carrying
   `"reason"`. The explicit flag is the **only** input that produces
   `"explicit_request"`; staleness produces `"module_cache_stale"`. Asserting
   `recovery.reason == "explicit_request"` with an unchanged module and no staleness
   proves the flag itself was honored rather than a coincidental staleness reset.

### Conclusion required by task 1.2

The observable **exists**. The flag is end-to-end observable through two independent
channels (JS global continuity, and the `recovery.reason` payload field), so the case can
fail. No need to stop and report the flag unobservable.

To keep the case honest it must use an **unchanged** module: rewriting the module would
make `CheckModuleStaleness()` non-empty, the default `auto-reset` policy would reset
anyway, and the case would pass without the flag ever being exercised.
