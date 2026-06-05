## 1. Runtime grouping fix (already applied — confirm & document)

- [x] 1.1 Confirm the `_parse_chunk` continuation loop in `cli/python/unity_log_brief.py` honors the blank-line boundary rule (non-indented frames + footer absorbed; level from header only) and matches the modified `log-brief` spec.
- [x] 1.2 Add source comments at the parsing site documenting the boundary rule AND the stack-trace-enabled assumption (what Unity emits with `ScriptOnly`/`Full` vs `None`, and why grouping depends on the post-footer blank). Reference `Application.GetStackTraceLogType` / `Console ▸ Stack Trace Logging`.

## 2. Test hardening against real-log shapes

- [x] 2.1 Strengthen `test_unity_style_non_indented_stacktrace` to assert the exact `line_count` (header + all frames + blank + footer, excluding the trailing blank before the next entry) instead of `> 1`.
- [x] 2.2 Add a multi-frame entry test using realistic frames with `(at ./path:line)` suffixes (≈8 frames) + blank + `(Filename: … Line: N)` footer; assert one brief with the correct level and `line_count`.
- [x] 2.3 Add a `Domain Reload Profiling` block test (non-indented header → back-to-back non-indented siblings → tab-indented children) asserting it collapses into one merged brief with a pinned `line_count`.
- [x] 2.4 Add a level-loss boundary test: an `[Error]` (and `[Warning]`) line directly following a non-blank non-indented line with no blank separator is merged into the prior brief and its level is NOT surfaced — pinning the stack-trace-OFF failure mode that motivates Section 3.
- [x] 2.5 Keep the existing `test_unity_style_blank_separated_entries_do_not_merge`; ensure all `tests/test_unity_log_brief.py` pass via `python -m unittest tests.test_unity_log_brief`.

## 3. Stack-trace-disabled detection (C# side)

- [x] 3.1 Verify `Application.GetStackTraceLogType(LogType)` compiles on the validation host; confirm the `StackTraceLogType.{None,ScriptOnly,Full}` enum surface. Record the result and flip `meta.yaml` `assumption_state` to `valid` (or capture the blocker). — Verified on c3-client-tree2 (Unity 2022.3.62f2): batch compile green, only pre-existing JsEnv-obsolete warnings. Runtime init also confirmed: server logged `[UnityPuerExec] Ready on port 55231` with the new assembly and no exception, so `Application.GetStackTraceLogType` in the static ctor / OnEditorUpdate (main thread) does not throw. `assumption_state` → `valid`, `evidence` → `host-validation`.
- [x] 3.2 In `UnityPuerExecServer.cs`, read `GetStackTraceLogType` for `LogType.Log`, `LogType.Warning`, `LogType.Error` and include them in the exec / wait-for-exec response payload (field name/shape finalized here per design Open Questions). — Sampled on main thread in `OnEditorUpdate`/static-ctor, spliced centrally in `WriteJsonAsync` as `stack_trace_logging`.
- [x] 3.3 Define the degraded condition as "any of the three == `None`" in one place so Python can consume a single boolean or derive it from the reported values. — `SampleStackTraceLogTypes` computes `_stackTraceLoggingDegraded`; reported as `stack_trace_logging.degraded`.

## 4. Degraded-state surfacing (Python flow)

- [x] 4.1 Choose the degraded `brief_sequence` sentinel token (outside the `I/W/E/?`+digits grammar) and the hint field name; document both. — Sentinel `!stacktrace-off`; hint field `brief_hint`.
- [x] 4.2 In `cli/python/unity_puer_exec_runtime.py` `_inject_log_range_into_payload` / `_inject_log_range_into_stdout`, when the payload reports degraded, set `brief_sequence` to the sentinel and add the hint field (enable `ScriptOnly`/`Full` via `Console ▸ Stack Trace Logging` or `Application.SetStackTraceLogType`). — Shared `_apply_log_range_and_brief_sequence` helper.
- [x] 4.3 Leave standalone `get-log-briefs --range` unchanged behaviorally; update its help/contract text to note unreliability when stack-trace logging is disabled. — Added a note to the `get-log-briefs` quick_start in `help_surface.py`.
- [x] 4.4 Add runtime tests covering both branches: degraded payload → sentinel + hint; non-degraded payload → normal `brief_sequence`, no hint. — `StackTraceDegradedBriefSequenceTests` (degraded, not-degraded, missing-field backward-compat, stdout round-trip).

## 5. Spec sync & closeout

- [x] 5.1 Ensure the implementation matches `specs/log-brief/spec.md` deltas (modified grouping requirement + added degraded-detection requirement, including the sentinel/hint scenarios).
- [x] 5.2 Run the full Python test suite; confirm green. — Default suite: 249 tests OK.
- [x] 5.3 Apply closeout: write the explicit finding summary (`No new follow-up work identified` or `New follow-up candidates identified` with categories) per the apply-closeout-review spec, and recommend (do not auto-run) the `git commit` / `openspec archive` / final `git commit` sequence.

### Closeout finding summary

**New follow-up candidates identified.**

- `validation-gap` — End-to-end detection round-trip is not yet observed on a live host. Both sides are green against the `stack_trace_logging.degraded` contract (C# compiles + server inits without throwing; Python unit tests cover degraded / not-degraded / missing-field / stdout round-trip), and the C# static-ctor sampling is runtime-confirmed via the server `Ready` line — but no real response has been observed emitting `stack_trace_logging`, nor the `!stacktrace-off` path firing with `StackTraceLogType.None` actually set. Recommended check: launch a non-batch editor on c3-client-tree2, `Application.SetStackTraceLogType(LogType.Log, StackTraceLogType.None)`, run one `exec`, and confirm `stack_trace_logging.degraded == true` and `brief_sequence == "!stacktrace-off"` in the response. Requires human-discussion per apply-closeout-review before acting.

**Recommended close sequence (not auto-run):** `git commit` (already staged incrementally) → `openspec archive improve-log-brief-stacktrace-fidelity` → final `git commit`. Defer archive if the human wants the live e2e validation done first under this change rather than as a follow-up.
