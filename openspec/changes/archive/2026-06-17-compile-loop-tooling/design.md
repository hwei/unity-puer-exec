## Context

The compile loop an agent runs after editing C# is: trigger a recompile, wait for it to finish, then read errors. Today the CLI supports the ends (`--refresh-before-exec` / a hand-written `AssetDatabase.Refresh()`; `get-compile-errors`) but not the middle "wait for compile" step, and the only timing signal is `/health` status.

Two concrete defects:

1. **Async-refresh race.** `AssetDatabase.Refresh()` (and `CompilationPipeline.RequestScriptCompilation()`) schedule compilation asynchronously. A caller that issues a refresh and immediately polls `/health` can observe `ready` *before* `compiling` ever appears, conclude "compile done", and read `get-compile-errors` — which still holds the *previous* compilation's messages (`compile-error-surface`: state resets only when `compilationStarted` fires). The fix is an **edge-aware** wait: do not treat the first `ready` as terminal; first confirm a compile cycle started.

2. **Refresh-before-exec is project-mode-only.** `validate_project_mode_only(selector, "refresh-before-exec", ...)` raises for base-url callers. But the server accepts `refresh_before_exec` in any selector, and the refresh template is plain CLI-injected JS. The only project-mode-specific code is `_ensure_project_session_ready_after_refresh(args)`, which re-acquires the session by `project_path` after the refresh-triggered domain reload. In base-url mode the analog is simply: re-probe the same caller-supplied endpoint until it is `ready` again — which is precisely the compile-wait primitive.

The current refresh-then-exec flow (`exec --project-path --refresh-before-exec`) already runs the user script after re-acquiring the session; the `{refreshed: true}` the caller sometimes sees is the intermediate refresh-exec response surfaced when the request goes non-terminal (refreshing/compiling) and the caller is expected to continue via `wait-for-exec`. This is a clarity gap, not a missing execution.

## Goals / Non-Goals

**Goals:**
- A `wait-for-compile` primitive that reliably brackets one compile cycle (compiling appears → returns to ready) across both selectors, defeating the async-refresh race.
- `--refresh-before-exec` usable in base-url mode, with a base-url settle path that reuses the compile-wait behavior.
- One coherent refresh→settle→execute lifecycle, with the non-terminal refreshing/`{refreshed: true}` state made explicit to callers.

**Non-Goals:**
- No new Unity server endpoint. The primitive composes existing `/health`.
- No change to the `refresh_before_exec` server contract or the `{refreshed: true}` server response shape (`compile-error-surface` stays as-is).
- No change to base-url identity semantics — base-url stays direct, single-endpoint, no project validation, no launch.
- Not range-aware session discovery — that is the sibling change `range-aware-session-discovery`.

## Decisions

### Decision 1: Edge-aware two-phase wait, not "wait until ready"

`wait-for-compile` runs a small state machine:

```
   start ──poll /health──► [appear window]
                              │ compiling seen? ──yes──► [settle] ──ready?──► done(ready)
                              │                                         └─ timeout ─► running/timeout
                              │ no compile within appear-window AND
                              └─ already ready, no edge ──► done(no_compile_observed)
```

- The **appear window** bounds how long we wait for `compiling` to show after a refresh, absorbing the async-start delay. If a compile is already in progress when we start, we go straight to settle.
- The **settle phase** waits for return to `ready` using the existing activity/ready timeout machinery.
- A terminal `no_compile_observed` outcome is distinct from `ready-after-compile`, so callers can tell "nothing recompiled" from "recompiled and clean".
- **Why over "poll until ready":** the naive version is exactly the racey behavior that produced stale errors. Requiring an observed edge (or an in-progress compile) before accepting `ready` is the whole point.

### Decision 2: Base-url settle = same-endpoint re-probe

In base-url mode, post-refresh readiness re-probes the caller-supplied endpoint (no range scan, no identity check — consistent with "Direct base-url mode remains explicit"). This is the same loop `wait-for-compile` uses, so refresh-before-exec in base-url mode is implemented as refresh → compile-wait(base_url) → exec.

- **Why over forbidding it:** the restriction was conservative, tied to the project-mode re-acquire helper, not to any base-url hazard. Refresh does not launch or change endpoint ownership, so it is compatible with the base-url contract.

### Decision 3: Reuse the primitive inside refresh-before-exec (both selectors)

Refresh-before-exec becomes: refresh-exec → compile-settle (compile-wait) → run user script. In project mode the settle still re-acquires the session (existing `_ensure_project_session_ready_after_refresh`, now expressed in terms of the compile-wait edge); in base-url mode it re-probes the same endpoint. This removes the divergence where base-url had no settle path at all.

### Decision 4: Make the non-terminal refreshing state explicit, keep server response intact

The server keeps returning `{"ok": true, "status": "completed", "result": {"refreshed": true}}` for the refresh step. The CLI clarifies — in help and in the lifecycle/`next_steps` output — that refreshing/compiling are non-terminal phases of the accepted exec request and that the script result arrives after settle, so a caller does not mistake `{refreshed: true}` for the script's return value.

### Decision 5: RequestScriptCompilation vs AssetDatabase.Refresh — documented, not silently switched

`RequestScriptCompilation()` triggers a recompile more deterministically than `AssetDatabase.Refresh()` (which only recompiles if it detects changed assets). Rather than silently change the refresh template's trigger, document the trade-off and keep the current `AssetDatabase.Refresh()` default; whether to expose an explicit trigger choice is an open question below.

## Risks / Trade-offs

- **[Compile finishes faster than the first poll]** an edge could be missed if compilation starts and ends entirely between two polls → mitigate with a short poll interval during the appear window and by also accepting evidence of a *completed-but-newer* compilation (e.g., session/compile markers) where available; document `no_compile_observed` so callers can decide to retry or proceed.
- **[Refresh does not actually recompile]** if no assets changed, `AssetDatabase.Refresh()` triggers no compile and `wait-for-compile` correctly reports `no_compile_observed` — surfacing this clearly avoids the "stale error" trap and points callers at `RequestScriptCompilation()` (Decision 5).
- **[Appear-window tuning]** too short misses slow-starting compiles, too long stalls the happy "nothing changed" path → make the appear window a bounded, overridable timeout with a sensible default, separate from the settle timeout.
- **[Domain reload mid-wait in base-url mode]** the endpoint briefly drops during reload → the re-probe loop tolerates transient connection failures the same way project-mode readiness does, treating them as still-in-progress until the ready/timeout boundary.

## Open Questions

- Should `wait-for-compile` optionally **trigger** the recompile (a `--refresh` flag) or stay a pure observer that callers pair with a separate refresh/exec? Leaning pure observer for composability, with refresh-before-exec as the integrated trigger+wait path.
- Should the refresh trigger be selectable (`AssetDatabase.Refresh()` vs `RequestScriptCompilation()`) via a flag, or stay fixed with documentation only? Leaning documentation-only for this change; expose a flag later if host validation shows the default misses real recompiles.
- Exact terminal vocabulary for the "no compile happened" outcome (`no_compile_observed` vs reusing an existing state) so it stays consistent with the established machine-state set.
