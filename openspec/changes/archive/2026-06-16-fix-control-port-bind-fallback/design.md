## Context

`UnityPuerExecServer.Start()` (`packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs`) scans a bounded port range (`PreferredPort` 55231, `MaxPortAttempts` 20) and binds the first available loopback port via `HttpListener`. The fallback was authored against .NET Framework / Windows http.sys behavior, where a port-in-use conflict surfaces as `HttpListenerException`. The loop reflects this:

```csharp
catch (HttpListenerException ex) { lastBindError = ex; /* warn + continue */ }
catch (Exception ex)            { lastBindError = ex; /* error */ break; }
```

The Unity Editor runs on **Mono**, whose `HttpListener` is a managed `System.Net.Sockets`-based implementation. A port-in-use conflict there throws `SocketException` (`0x80004005`, `SocketError.AddressAlreadyInUse`), which is **not** an `HttpListenerException`. It therefore falls into the generic `catch`, which `break`s — aborting the scan after the first occupied port. Field evidence: `AssetImportWorker0.log` shows `Unexpected error binding port 55231: System.Net.Sockets.SocketException` immediately followed by `Failed to bind any port in range 55231-55250`, while `AssetImportWorker1.log` shows `Ready on port 55231`. Ports 55232-55250 were never tried. Net effect: the entire fallback is dead under Unity — the `catch (HttpListenerException)` arm is effectively unreachable.

Second, contention is amplified because `[InitializeOnLoad]` runs in every Unity process, including batch-mode `AssetImportWorker` subprocesses. These workers also run `Start()` and race for the preferred port; a worker can win 55231 and squat on it for its lifetime, so an external CLI probing 55231 may reach a transient worker rather than the interactive Editor.

## Goals / Non-Goals

**Goals:**
- Make the bounded port-fallback scan actually roll over on port-in-use under Mono, satisfying the existing `project-control-endpoint` rollover requirement.
- Prevent batch-mode / asset-import worker subprocesses from starting the control service and contending for the preferred port.
- Keep the failure log honest about how many ports were attempted.

**Non-Goals:**
- No change to dynamic port range bounds (`PreferredPort`, `MaxPortAttempts`).
- No change to health identity fields, protocol wire format, or CLI routing.
- No attempt to coordinate ports across multiple interactive Editors beyond the existing range scan.

## Decisions

### Decision 1: Treat `SocketException` (and any port-in-use bind error) as "try next port", not as fatal

Rework the `catch` arms so a bind failure attributable to a port-in-use condition continues the loop. Concretely: catch `SocketException` (logging at warning level, like the existing `HttpListenerException` arm) and `continue`; keep the `HttpListenerException` arm for cross-runtime safety; reserve `break` for unexpected fatal exceptions only.

- Rationale: The conflict type is runtime-dependent (Mono `SocketException` vs http.sys `HttpListenerException`). Keying control flow on the concrete type is the root defect. Handling both keeps the package correct on both Editor (Mono) and any future runtime.
- Alternative considered: catch all `Exception` and always `continue`. Rejected — that would mask genuinely fatal misconfiguration (e.g. permission/ACL errors) by silently churning through the whole range and then failing with a misleading "range exhausted" message. Distinguishing port-in-use from fatal keeps diagnostics meaningful.
- Note: under Mono, `SocketException` is the dominant path; the `HttpListenerException` arm becomes defensive. We should not rely on `SocketError.AddressAlreadyInUse` exclusively — any `SocketException` during `Start()` of a candidate is safe to treat as "this port didn't work, try the next" because each attempt uses a fresh `HttpListener`.

### Decision 2: Skip `Start()` in non-interactive (batch-mode) processes

Guard early in `Start()` (or before scheduling it from the static constructor) with `Application.isBatchMode`. Asset-import workers run with `-batchMode`, so this cleanly excludes them while leaving the interactive Editor unaffected.

- Rationale: `Application.isBatchMode` is the supported, stable signal for non-interactive Unity processes and is true for `AssetImportWorker` subprocesses. It avoids brittle command-line sniffing for `-name AssetImportWorker`.
- Alternative considered: parse the process command line for `AssetImportWorker`. Rejected as fragile and worker-name-specific; `isBatchMode` covers the general non-interactive case (workers, CI batch runs) which should not host an interactive control endpoint anyway.
- Consequence: a headless/batch invocation will not expose the control service. That is acceptable — the endpoint targets interactive Editor sessions; batch runs are not the product's control surface.

### Decision 3: Honest failure message

When the scan exhausts the range, the failure log already names the range. Ensure the message is only emitted after the loop genuinely tried each port (a natural consequence of Decision 1). No separate attempt counter is required once rollover works, but the message should not imply success was possible on untried ports.

## Risks / Trade-offs

- [A real fatal error (e.g. ACL/permission) now gets retried across the range before failing] → Mitigation: only port-in-use exception types (`SocketException`, `HttpListenerException`) continue the loop; other exception types still `break` immediately, preserving fast, accurate failure for genuinely fatal conditions.
- [`Application.isBatchMode` might exclude a legitimate headless use case someone relies on] → Mitigation: none currently known; the control endpoint is defined for interactive Editor sessions. If a headless need emerges, it can be reintroduced behind an explicit opt-in env/define in a follow-up.
- [Mono may raise a `SocketException` for a non-contention reason during `Start()`] → Mitigation: each candidate uses a fresh `HttpListener` and is independent; treating a failed candidate as "skip to next" is safe, and a truly unbindable environment still ends in the range-exhausted failure with the last error attached.

## Migration Plan

- Pure in-process behavior fix; no data, artifact, or wire-format migration.
- Rollout is the package update itself. Rollback is reverting the source change.
- Validation: on a Unity/Mono host, occupy 55231 with another listener, load the package in the interactive Editor, and confirm it binds 55232+ and reports it via `/health`; confirm an asset-import worker subprocess binds no port in range. See `openspec/specs/validation-host-integration/how-to-run.md`.

## Open Questions

- None blocking. (If a future headless control-endpoint use case appears, revisit Decision 2 with an explicit opt-in rather than removing the guard.)
