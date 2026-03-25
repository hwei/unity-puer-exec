## Context

The CLI already exposes `wait-for-log-pattern`, `--start-offset`, and `get-log-source` for log observation. Prompt B help-only validation runs archived under `improve-wait-for-log-pattern-stall-guidance` showed that agents repeatedly abandon the CLI surface after `unity_stalled` outcomes because they have no way to see what happened in the log during the operation without inspecting `Editor.log` directly. The root gap is not stall-recovery guidance but the absence of a CLI-native log summary for any exec operation window.

## Goals / Non-Goals

**Goals:**
- Give agents a compact log-activity summary (`brief_sequence`) for every exec and wait-for-exec response without requiring extra commands.
- Give agents a way to fetch structured brief entries for any log offset range (`get-log-briefs`).
- Replace the opt-in `log_offset` / `--include-log-offset` pattern with an automatic `log_range` field.
- Keep brief parsing robust enough to be useful even when log format details are ambiguous.

**Non-Goals:**
- Do not redesign `wait-for-log-pattern` or `wait-for-result-marker`.
- Do not add streaming or incremental brief delivery.
- Do not support log formats beyond the Unity Editor log.
- Do not attempt full log message extraction beyond the 100-character text preview.

## Decisions

### Decision: log_range replaces log_offset and is always present

`exec` and `wait-for-exec` responses include `log_range: { start, end }` unconditionally. `start` is set when the CLI begins observing the log for the request. `end` is the latest observed log position at response time — never null, even for in-progress responses. The `--include-log-offset` flag and `log_offset` field are removed.

**Why**: Agents need both start and end to use `get-log-briefs`. Making it always present removes a flag agents have to remember. Using `end` = current tail for in-progress responses means agents can query briefs for "what happened so far" at any checkpoint.

**Alternative considered**: Keep `log_offset` and add `log_end_offset` separately. Rejected because two separate offset fields are harder to reason about than a single `log_range` object.

### Decision: brief_sequence is a compact level string, always present

Each exec and wait-for-exec response includes `brief_sequence`: a string where each character represents one parsed log entry within `log_range`. Values: `I` (info), `W` (warning), `E` (error), `?` (one or more consecutive unrecognized entries, merged). Example: `"IIW?EEI"`.

**Why**: Agents can scan the string and immediately know whether errors or warnings occurred without any extra call. The `?` merge prevents long unknown sections from producing unwieldy sequences. Indices into the string are 1-based and map directly to `--include` values for `get-log-briefs`.

**Alternative considered**: Return briefs inline in exec response. Rejected because brief payloads can be large and most agents only need the summary to decide whether to dig deeper.

### Decision: get-log-briefs uses --range and optional --levels / --include filters

`get-log-briefs --range=START-END` returns all briefs for the offset range. `--levels=error,warning` filters by level. `--include=1,3,4` selects specific 1-based indices. When both are supplied, results are their union. `--range` also accepts comma-separated form (`START,END`).

**Why**: `--range` mirrors the `log_range` field shape, reducing cognitive load. Union semantics for `--levels` + `--include` let agents say "all errors, plus also entry #3 I noticed" without needing two calls.

### Decision: Three-layer log parsing with documented fallback behavior

Parsing applies rules in order:
1. **Section-aware**: detect known section markers (`-----CompilerOutput:` / `-----EndCompilerOutput`, etc.) and apply section-specific rules.
2. **Traceback-based**: split by blank-line + non-indented-line boundary; derive level from log type markers.
3. **Unknown fallback**: emit a single merged `?` brief for consecutive unrecognized lines.

**Why**: C# compile output and runtime Unity logs have structurally different formats; applying the wrong rule produces misleading briefs. Documented fallback to `?` means agents always know when parsing confidence is low, rather than receiving silently wrong level assignments.

### Decision: Brief text is capped at 100 characters

Each brief `text` field contains the first 100 characters of the entry's first line. `unknown` briefs have `text: null`.

**Why**: 100 characters covers `path(line,col): error CSXXXX:` plus the start of the message for typical compile errors, which is enough for an agent to identify the file and error code without needing the full message.

### Decision: brief line_count field covers merged entries

Every brief includes `line_count`: the number of raw log lines it covers. For normal entries this is 1 or the traceback depth. For merged `?` groups this reflects the actual number of unrecognized lines collapsed.

**Why**: Agents querying a `?` group need to know whether it covers 1 or 50 lines to decide if it is worth fetching the raw range via `get-log-source`.

## Risks / Trade-offs

- **Unity log format changes** → Parsing rules may silently degrade to `?`. Mitigation: document the known section markers and traceback patterns explicitly in the spec so regressions are detectable.
- **Long compile phases with many warnings** → `brief_sequence` can be long. Mitigation: the string is still much more compact than raw log lines; agents can filter with `--levels` to reduce `get-log-briefs` payloads.
- **log_range.end for in-progress responses** → End offset is a snapshot, not a guarantee that all log lines before it have been parsed. Mitigation: document that `end` is a best-effort tail position; agents should re-query with updated `log_range` from later responses if they need fresher coverage.
- **BREAKING removal of log_offset** → Callers using `--include-log-offset` must migrate to `log_range.start`. Mitigation: product is pre-release; no external callers to coordinate with.

## Open Questions

- Asset import and build pipeline log section markers are not yet fully catalogued. Initial implementation may fall back to traceback parsing for those sections; a follow-up can add dedicated rules once the formats are confirmed.
