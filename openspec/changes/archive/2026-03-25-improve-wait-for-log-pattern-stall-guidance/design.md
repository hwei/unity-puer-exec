## Context

`exec` and `wait-for-exec` already return `log_range` + `brief_sequence` on every exit path. The three wait commands (`wait-for-log-pattern`, `wait-for-result-marker`, `wait-until-ready`) do not, leaving agents without structured log context for diagnosis.

## Goals / Non-Goals

**Goals:**
- All three wait commands return `log_range` + `brief_sequence` on every exit path (success, stall, timeout, other failures).
- `wait-until-ready` gains `--start-offset` (default=None → auto-capture log end at invocation), aligning its interface with the other wait commands.
- Uniform diagnostic output contract across all five observation commands.

**Non-Goals:**
- Do not change `exec` or `wait-for-exec` behavior (already complete).
- Do not redesign the log-observation subsystem or brief infrastructure.

## Design Constraints

1. **DRY**: The log_range + brief_sequence injection logic already exists (`_inject_log_range_into_payload`, `_inject_log_range_into_stdout`). The log_path resolution logic already exists (`_resolve_exec_log_path`). Reuse and generalize rather than duplicate.

2. **Single responsibility**: Each wait function owns its own exit paths and log context. The generic exception handler in `run_command` remains as a safety net but should not be the expected path for producing structured diagnostics.

3. **Performance**: `parse_log_briefs` reads a byte range from disk. The observation window (log_start → log_end) is already bounded by the command's lifetime, so no extra work is needed to limit the scan. Avoid capturing log_end until the moment of injection (lazy), so it reflects the actual observation window.

## Decisions

### Decision: Generalize `_resolve_exec_log_path` for all commands

The current fallback chain (session.effective_log_path → args.unity_log_path → default) is correct for wait commands too. Rename to a general name so all commands share one resolution path.

### Decision: Capture log_start early, log_end late

Each wait function captures `log_start` at invocation (from `--start-offset` or current log size), and captures `log_end` at the moment of injection. This matches the exec pattern and accurately reflects the observation window.

### Decision: Judge against host-log fallback

Prompt B already succeeds. The acceptance question is whether the change reduces the need for direct `Editor.log` inspection after `unity_stalled`.
