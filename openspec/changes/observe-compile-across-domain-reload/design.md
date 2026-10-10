## Context

`wait_for_compile_cycle` observes a compile by seeing `compiling` appear and then `ready`,
or by seeing a previously-ready endpoint drop. After play-mode exit, the deferred compile
ends in a domain reload that stops the listener: the endpoint is down across the whole
compile, and when it returns the Editor is `ready` and the pending change has cleared.

The validation-host reproduction (`validation.md` in the archived
`surface-play-mode-compile-block`) measured the deferred compile as an ~15.5 s unreachable
window with play exit observed at ~57.6 s. `wait-for-compile` invoked in that state returned
`no_compile_observed`.

## Hypotheses to investigate

1. The pending signal clears as part of the reload, before the CLI could take a baseline.
2. A server-side compile epoch (incremented on `compilationFinished`) is enough for a caller
   that took a baseline before the reload, but not for one that starts after.
3. The persisted settle timestamp (`UnityPuerExec.SettledImportUtcTicks` in `SessionState`)
   survives the reload and can serve as a comparable "compiled after T" signal.
4. The honest answer is that a post-reload caller cannot distinguish the two cases, and the
   fix is to make the CLI drive the transition (so it always has a baseline) rather than to
   make a late call succeed.

## Investigation result

Validation host `F:\C3\unity-puer-exec-workspace\c3-client-tree2\Project`, Unity 2022.3.62f2,
bridge 0.9.0, `ScriptCompilationDuringPlay = recompile_after_finished_playing`. Procedure
(`.tmp/observe_compile_reload_probe.py`): enter play mode, write a real compile-triggering
`.cs` under `Assets/__codex_validation_temp/`, wait for `refresh.pending = pending` +
`suppressed_reason = play_mode`, then request `EditorApplication.isPlaying = false` through
`exec` and poll `/health` at ~0.15 s plus `/health.refresh.pending` and the resolved port
until reconnection.

### Timeline (definitive run; times relative to the play-exit request)

| t | `/health` | evidence |
|---|---|---|
| 1.57 s | `ready`, `pending=pending`, `suppressed=true` | still in play mode |
| 4.98 s | `ready`, `pending=not_pending`, `suppressed=true` | `compilationFinished` fired; the tracker advanced its settled threshold and cleared pending **while the listener was still bound** |
| 5.40 s | unreachable | `beforeAssemblyReload` stopped the listener |
| 54.79 s | `ready`, `pending=not_pending`, `suppressed=false` | the new domain rebound, published a new `session_marker`, and served a ready response |

The endpoint was unreachable for ~49 s. **No `compiling` status was ever served** in any run:
the compile is Unity's "forced synchronous recompile", and `beforeAssemblyReload` fires at the
start of it, so the listener is down before the compile completes and only rebinds after the
reload.

Project-private `Editor.log`, same window (temporary instrumentation removed after the run):

```
[ScriptCompilation] Requested script compilation because: Assetdatabase observed changes ...
[SpikeProbeReload] compilationFinished fired gen=1          <- fires BEFORE the reload
Reloading assemblies after forced synchronous recompile.
Begin MonoManager ReloadAssembly
[UnityPuerExec] Ready on port 55232
[SpikeProbeReload] afterAssemblyReload fired persistedGen=1 <- generation survived the reload
Scripting: domain reloads=1, domain reload time=47940 ms, compile time=3691 ms
```

After reconnection, a read of `UnityEditor.SessionState` reported
`SpikeProbeCompileGen = 1` and an advanced `UnityPuerExec.SettledImportUtcTicks`
(baseline `639272143600364477` -> `639272145130634908`, +153.03 s of wall clock across the
whole procedure). `wait-for-compile` invoked after reconnection returned
`status: no_compile_observed`, `compile_observed: false` — the false negative reproduced.
The `session_marker` changed across the reload (`876d5db1...` -> `0f4e8dff...`).

### Control

Exiting play mode with **no** pending change (clean run, `.tmp/observe_compile_control_probe.py`)
produced **no** reload: the endpoint stayed reachable, and both `session_marker` and the
settled-import ticks were unchanged. A contaminated control (a leftover script **deletion**)
did produce a compile + reload on play exit while `refresh.pending` read `not_pending`,
which shows that excluded filesystem changes can compile without a positive pending signal.

### Signal comparison

| Candidate | Usable? | Reason |
|---|---|---|
| `session_marker` (existing `/health`) | partly | Changes on **every** domain reload, not only compiles (`EditorUtility.RequestScriptReload()` reloads without compiling), and needs a pre-reload baseline. Usable only as a coarse "a reload happened since T" check. |
| `settledImportUtcTicks` (`SessionState`, not exposed) | no | Advanced by **both** `compilationFinished` and `afterAssemblyReload`, so it is a reload epoch, not a compile epoch; not on `/health`. |
| `refresh.pending` baseline | no | `compilationFinished` clears pending **before** the drop, and an excluded change such as a script deletion compiles across the reload while `pending` reads `not_pending`. |
| A new compile generation incremented only on `compilationFinished` | **yes** | Fires pre-reload for the deferred compile (verified), survives the reload through `SessionState`, and is observable after reconnection. |
| CLI-driven baseline before play exit | **yes** | The command that drives the play exit holds the generation baseline in-process, so it needs no cross-invocation state. |

## Decisions

### D1. Root cause

A deferred play-exit compile cannot be observed through `/health` as it happens: the
control listener is stopped by `beforeAssemblyReload` for the whole compile+reload, so the
`compiling` status is never served and the only pre-reload signal is a brief `ready` +
`not_pending` response that a caller is not guaranteed to catch. `wait-for-compile`'s
edge detection therefore sees only `ready` and returns `no_compile_observed`. Confirmed by
the timeline above.

### D2. Chosen approach: a compile generation reported on `/health`

Add a monotonic **compile generation** to the Unity control service, incremented only when a
script compilation completes (`CompilationPipeline.compilationFinished`), persisted in
`SessionState` so it survives the reload, and exposed on the ready `/health` response
(alongside `refresh` or as a `compile` block). A CLI command that drives the transition it
cares about (the `stop` command from `add-play-mode-commands`) reads the generation before
posting the exit and, after the endpoint returns, reports `compile_settled` when the
generation advanced past that baseline. This is the only candidate that is both
compile-specific and observable across the reload; the verified event ordering
(`compilationFinished` before `beforeAssemblyReload`) is what makes the persisted counter
correct.

### D3. Rejected alternatives

- **Reuse `session_marker` as the epoch.** It is a domain-load identity, not a compile
  identity: `EditorUtility.RequestScriptReload()` advances it without compiling. It would
  turn "a reload happened" into "a compile happened".
- **Reuse `settledImportUtcTicks`.** `OnAfterAssemblyReload` advances it on every reload, so
  it has the same false positive as the marker, and it is not on `/health`.
- **Baseline on `refresh.pending` only.** Rejected by evidence: the value clears at
  `compilationFinished` before the listener drops, and an excluded change (script deletion)
  compiles while `pending` reads `not_pending`.
- **A settle marker keyed to the request.** Same reload/compile conflation, plus it needs
  request-scoped state that a later `wait-for-compile` does not have.

### D4. Caller-facing outcome

Keep `compile_settled` with `compile_observed: true` when the generation advanced. The
`compile-wait` contract requires that "an initial `ready` is never terminal before an edge
is observed"; a generation advance **is** an observed edge, so the contract is honored, not
amended. Add a non-breaking field naming how the edge was seen (for example
`edge: "generation_advance"` versus `edge: "observed_drop"`) so a caller can tell an
inferred-across-reload settle from a directly-observed one. Do **not** invent a new terminal
status; callers already branch on `compile_settled` / `no_compile_observed`.

### D5. Scope

The guarantee is scoped to the **CLI-driven sequence**: a command that holds a generation
baseline from before the reload (the `stop` command, or a `wait-for-compile` given an
explicit baseline) reports `compile_settled`. A caller that starts **after** the reload and
supplies no baseline cannot distinguish "compiled across the reload" from "nothing
compiled"; for that caller `wait-for-compile` keeps returning `no_compile_observed`. This
scope is part of the durable requirements rather than an implied limitation. A persistent
CLI-side baseline (remembering the last generation per project) is possible future work, not
part of this change.

## Open Questions

- Resolved by this investigation: the pending signal clears before the reload
  (`compilationFinished`), not after it; a server-side compile epoch is worth the protocol
  field; and the outcome stays `compile_settled` with the edge source disclosed.

## Hand-off

The recommended implementation (server-side compile generation on `/health`, plus the
`wait-for-compile` inferred-settle outcome and its tests) is carried by the follow-up change
`add-compile-generation-signal`. This spike closes with the finding above.
