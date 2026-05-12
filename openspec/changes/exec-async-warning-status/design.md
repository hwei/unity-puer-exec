## Context

When the PuerTS runtime executes a user script via `exec`, the C# harness wraps the user's module. The harness calls `__entry(__ctx)` (the user's default-exported function) and captures the return value. Currently, if that return value is a thenable (e.g. `async function` returns a Promise), the harness throws `Error('async_result_not_supported')`, which triggers `FailJob`. The job status becomes `Failed`, the response has `ok:false, status:"failed"`, and the CLI maps this to exit code 1 with output on stderr.

The problem: `__entry(__ctx)` has already been called before the thenable check. The function body executed — all synchronous side effects (GameObject modifications, scene changes, console.log calls) have already taken effect. But the `failed` response tells the agent the opposite. No `log_range` is included, so even console.log evidence is invisible.

## Goals / Non-Goals

**Goals:**
- Introduce a `CompletedWithWarning` terminal job state that distinguishes "script ran, result not captured" from genuine failures.
- The protocol response for Promise returns uses `ok:true, status:"warning"` with `warning` code and human-readable `warning_detail`.
- CLI maps `warning` → exit code 0, response on stdout (same as `completed`).
- `BuildErrorDetailJson` extended to cover `async_result_not_supported` so the response JSON itself is self-explanatory.
- Help text and guidance matrix updated to reflect the distinction.

**Non-Goals:**
- Do not add automatic Promise awaiting. Async workflows continue to use `wait-for-result-marker`.
- Do not change the behavior of non-Promise failures (genuine exceptions, missing exports, etc.) — those remain `failed`.
- Do not introduce general-purpose warning infrastructure beyond the Promise case. The `warning` status is implemented for async result specifically, but the job state model is extensible.

## Decisions

### Decision 1: New job status `CompletedWithWarning` rather than repurposing `Completed`

**Rationale**: `Completed` currently carries the user's return value in `result`. A Promise return has no serializable result. Mixing a notice message into `result` would break the contract that `result` is the user's value. A separate status keeps the semantics clean for both sides.

**Alternative considered**: Overload `Completed` with a `__notice` result object. Rejected because callers parsing `result` would need to handle magic keys, and the semantics of "completed without a real result" are clearer as a distinct status.

### Decision 2: Protocol shape for warning responses

```json
{
  "ok": true,
  "status": "warning",
  "request_id": "...",
  "session_marker": "...",
  "warning": "async_result_not_supported",
  "warning_detail": "...",
  "result": null
}
```

- `ok: true` because the script did execute.
- `status: "warning"` is the new terminal state.
- `warning` is the machine-readable code (stable for programmatic handling).
- `warning_detail` is the human-readable explanation (may evolve).
- `result: null` because no user value was captured.

**Alternative considered**: Use `ok:false` with `status:"warning"`. Rejected because `ok:false` signals failure; the script did not fail, it just couldn't return a value.

### Decision 3: Exit code 0 for warning

**Rationale**: The script executed successfully. Exit code 0 with stdout output keeps the response in the normal processing path (guidance injection, log_range attachment). This is consistent with `completed` and `running`.

### Decision 4: Harness JS uses if-else, not fall-through

The current harness does early throw on thenable. The new version must branch:

```javascript
const __result = __entry(__ctx);
const __isThenable = ...;
if (__isThenable) {
    __bridge.CompleteJobWithWarning(__jobId, 'async_result_not_supported', '...');
    // Do NOT continue to JSON.stringify / CompleteJob
} else {
    // existing synchronous result path
}
```

### Decision 5: Guidance matrix gets a dedicated `("exec","warning")` entry

Rather than lumping warning into the `("exec","failed")` entry (which would still mislead), a separate entry tells the agent exactly what happened:

```
("exec","warning"): {
    "situation": "The script body executed successfully, but the entry function returned a Promise (async_result_not_supported). Any synchronous side effects have already taken effect. Use console.log with wait-for-result-marker for async result observation."
}
```

## Risks / Trade-offs

- **Agent confusion if warning_detail is too long**: Keep it concise — 2-3 sentences max.
  → Mitigation: Edit for brevity, test with realistic agent prompts.
- **Protocol backward compatibility**: Consumers that check `status == "completed"` will not match `"warning"`.
  → Mitigation: `ok:true` and exit 0 are the primary signals. The `warning` status is additive; existing consumers that only check `ok` are unaffected. Consumers that switch on `status` need to handle the new value, but this is a documented protocol extension.
- **`wait-for-exec` sees warning**: The same snapshot is returned by `wait-for-exec`. Since warning is a terminal state, `wait-for-exec` returns immediately with the warning response.
  → This is correct behavior — the request is done, no further waiting needed.
- **Future warning codes**: The job state model supports additional warning codes beyond `async_result_not_supported`.
  → This is a feature, not a risk. The infrastructure is general-purpose.
