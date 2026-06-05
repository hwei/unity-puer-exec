## Why

Runtime log briefs over-count Unity stack traces: every non-indented stack-frame line was treated as a new log entry, so four `Debug.Log` calls produced a `brief_sequence` like `I103?` instead of `I5?`. The `add-log-brief-capability` design already specified the boundary rule as "blank-line + non-indented-line boundary" (`openspec/changes/archive/2026-03-25-add-log-brief-capability/design.md`), but the implementation broke on any non-indented line, ignoring the blank-line prerequisite. Separately, this whole grouping model only works when Unity emits stack traces; when stack-trace logging is disabled, `Debug.Log` output collapses into bare back-to-back lines that the parser cannot delimit, and today it silently produces misleading briefs with no signal to the operator.

## What Changes

- **FIX (already applied in working tree, validated against a real `Editor.log`):** Runtime traceback grouping honors the documented "blank-line + non-indented-line boundary" rule. Non-indented Unity stack-frame lines, and the trailing `(Filename: ... Line: N)` footer that Unity appends after a blank separator, are consumed into the current entry instead of starting a new brief. Entry level is still derived solely from the entry's first line.
- **NEW: stack-trace-disabled detection via Unity Editor API.** The C# server reports `Application.GetStackTraceLogType(LogType.Log/Warning/Error)`; if **any** of the three is `StackTraceLogType.None`, the condition is "degraded." Detection is deliberately C#-side, **not** a Python heuristic — real `Editor.log` contains back-to-back non-indented native noise (Mono reload, `Domain Reload Profiling`, Bee build lines) even when stack traces are ON, so a structural heuristic would false-positive on any quiet range.
- **NEW: degraded-state surfacing in exec / wait-for-exec.** When the C# response reports a degraded state, the exec / wait-for-exec flow sets `brief_sequence` to a sentinel and adds a hint field telling the operator to enable `ScriptOnly`/`Full` stack-trace logging (via `Console ▸ Stack Trace Logging` or `Application.SetStackTraceLogType`).
- **Standalone `get-log-briefs --range`** has no C# handshake and cannot consult the setting; its contract documents that results are unreliable when stack traces are disabled. No behavior change there beyond documentation.
- **Test hardening** against real-log shapes: a multi-frame entry (`Type:Method (at ./path:line)` frames) + blank + footer; the `Domain Reload Profiling` block merging into one brief with a pinned `line_count`; and an `[Error]`/`[Warning]` line directly following a non-blank non-indented line with no blank separator, pinning the level-loss boundary that motivates the detection feature.
- **Source comments** documenting the stack-trace-enabled assumption and the boundary rule at the parsing site.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `log-brief`: Tighten the runtime traceback boundary requirement to the documented blank-line rule (stack frames + footer belong to the current entry); add a requirement that the parser/observation surface reports a degraded state with operator guidance when Unity stack-trace logging is disabled, detected via the Unity Editor API rather than a heuristic.

## Impact

- `cli/python/unity_log_brief.py` — runtime grouping fix (done); comments.
- `cli/python/unity_puer_exec_runtime.py` — `_inject_log_range_into_*` consumes the degraded signal, emits sentinel `brief_sequence` + hint.
- `packages/com.txcombo.unity-puer-exec/Editor/UnityPuerExecServer.cs` — report `GetStackTraceLogType` for Log/Warning/Error in the exec/wait response payload.
- `tests/test_unity_log_brief.py` (+ runtime tests as needed) — hardened real-log shapes and degraded-state behavior.
- `openspec/specs/log-brief/spec.md` — durable requirement deltas.
- Verification dependency: the exact `Application.GetStackTraceLogType` getter signature must be confirmed to compile on the validation host (Unity Editor) before the C# side ships; `meta.yaml` carries `assumption_state: needs-review` until then.
