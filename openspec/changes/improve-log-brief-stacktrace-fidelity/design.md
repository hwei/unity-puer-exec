## Context

Log briefs summarize the Unity Editor log so agents can scan `exec` / `wait-for-exec` activity via `brief_sequence` without reading raw logs. Briefs are produced entirely in Python (`cli/python/unity_log_brief.py`), invoked from the runtime flow at `_inject_log_range_into_*` in `cli/python/unity_puer_exec_runtime.py`. The C# server (`UnityPuerExecServer.cs`) emits log lines via `Debug.Log/LogWarning/LogError` and returns a JSON payload that the Python flow annotates with `log_range` + `brief_sequence`.

Two problems, confirmed against a real `Editor.log` from the validation host:

1. **Over-counting stack frames.** The runtime grouping code broke an entry on *any* non-indented line, ignoring the documented "blank-line + non-indented-line boundary" rule. Real Unity `Debug.Log` output is `header → non-indented stack frames → blank → (Filename: … Line: N) → blank → next entry`. Treating each frame as a new entry yielded sequences like `I103?` for a handful of logs. (Fix already applied in the working tree.)

2. **Stack-trace-disabled blind spot.** The grouping rule only works because each entry is delimited by the blank line that follows its stack trace + footer. When `StackTraceLogType.None` is set, `Debug.Log` output is bare back-to-back lines with no delimiter, and briefs become silently misleading with no operator signal.

## Goals / Non-Goals

**Goals:**
- Make runtime grouping honor the documented boundary rule and validate it against real-log shapes.
- Detect stack-trace-disabled precisely and surface an actionable hint where the operator watches briefs (exec / wait-for-exec).
- Pin the failure-mode boundaries with tests so neither regresses.

**Non-Goals:**
- Parsing or grouping Unity native-noise blocks (Mono reload, Domain Reload Profiling, Bee build output) into semantically distinct briefs. These remain coarse merged briefs; that is acceptable for a health indicator.
- Making standalone `get-log-briefs --range` stack-trace-aware. It has no C# handshake; it stays a raw-range parser and only documents the limitation.
- Changing the `brief_sequence` run-encoding for the normal (non-degraded) path.

## Decisions

### Decision 1: Continuation-by-default boundary, level from header only

A non-indented line is a **continuation** unless preceded by a blank line; the `(Filename: …)` footer is consumed across its leading blank. Entry level is computed from the header line only, so an absorbed frame containing "Exception"/"Error" cannot flip the level. This restores the `add-log-brief-capability` design intent rather than inventing a new rule.

*Alternative considered — pattern-match stack frames* (`Type:Method (...)`, `at … in …`): rejected as fragile across Unity versions/localizations and unnecessary once the blank-line rule is honored.

### Decision 2: Detect stack-trace-disabled in C#, never by Python heuristic

The precise signal is `Application.GetStackTraceLogType(LogType.Log/Warning/Error)`. The server logs at all three levels (lines 199/209/219), so the degraded condition is **any of the three == `None`**.

*Alternative considered — Python heuristic* ("no footers / no frames in this range ⇒ disabled"): **rejected with evidence.** The real `Editor.log` contains back-to-back non-indented native lines (e.g. `Mono: successfully reloaded assembly` / `- Finished resetting the current domain` / `Domain Reload Profiling: 4602ms`) even with stack traces ON. A heuristic cannot distinguish disabled-Debug.Log output from an ordinary quiet/native range and would false-positive on healthy logs.

### Decision 3: Surface only where a C# payload exists; sentinel + hint

The setting is only knowable where the response payload is in hand — the exec / wait-for-exec flow. There, on degraded, set `brief_sequence` to a documented sentinel (distinct from any real encoding) and add a hint field. The sentinel must be unambiguous versus the `I/W/E/?` + count grammar so callers never mistake it for real activity. Standalone `get-log-briefs` documents the limitation only.

### Decision 4: C# → Python transport

The C# server adds the three `StackTraceLogType` values to its exec/wait response payload (e.g. a `stack_trace_log_type` object keyed by level, or a single `stack_trace_degraded` boolean plus detail). The Python flow reads it in `_inject_log_range_into_payload` / `_inject_log_range_into_stdout` and decides sentinel-vs-normal there. Exact field name/shape is finalized in apply against the existing payload schema.

## Risks / Trade-offs

- [Unity API signature unverified in this repo] → `meta.yaml` carries `assumption_state: needs-review`; an apply task confirms `Application.GetStackTraceLogType(LogType)` compiles on the validation host before shipping the C# side. The managed enum `StackTraceLogType.{None,ScriptOnly,Full}` is well established; only the getter is gated.
- [Setting reflects query time, not the whole range's history] → A caller could toggle the setting mid-range. Accept: the degraded flag describes the current observation window for a live health check, not a historical audit. Spec wording avoids over-claiming.
- [Native-noise blocks merge into one coarse brief] → Accepted non-goal. Errors/warnings in the stack-trace-ON format are always preceded by the post-footer blank, so the merge cannot swallow a real `[Error]`/`[Warning]` boundary. The only case where a level is silently lost is precisely stack-trace-OFF — which Decision 2/3 now flags explicitly. A dedicated test pins this boundary.
- [Sentinel collides with future encoding] → Choose a sentinel outside the `I/W/E/?`+digits grammar and assert it in tests.

## Open Questions

- Final payload field name/shape for the C# report (resolve in apply against the current response schema).
- Exact sentinel token and hint-field name (resolve in apply; must be covered by spec scenarios + tests).
