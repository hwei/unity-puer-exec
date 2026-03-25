## Why

The `exec` and `wait-for-exec` commands already return `log_range` + `brief_sequence` on every exit path (success, stall, timeout, error), giving agents structured diagnostic context to make recovery decisions without reading raw `Editor.log`. The three wait commands — `wait-for-log-pattern`, `wait-for-result-marker`, and `wait-until-ready` — lack this capability entirely. When any of them encounters a stall or timeout, the agent gets only a bare `unity_stalled` status and must fall back to direct log inspection.

## What Changes

- All three wait commands (`wait-for-log-pattern`, `wait-for-result-marker`, `wait-until-ready`) return `log_range` + `brief_sequence` on every exit path: success, stall, timeout, and other failures.
- `wait-until-ready` gains a new `--start-offset` parameter (default=None → auto-capture current log end at invocation time), aligning its interface with the other wait commands.
- The diagnostic output contract becomes uniform across all five observation commands (exec, wait-for-exec, and the three waits).

## Capabilities

### Modified Capabilities
- `log-brief`: wait commands gain the same log_range + brief_sequence output that exec/wait-for-exec already provide.
- `agent-cli-discoverability-validation`: agents can stay inside the CLI surface for post-stall diagnosis across all commands, not just exec.

## Impact

- Eliminates the diagnostic blind spot that forced agents to fall back to raw `Editor.log` after `unity_stalled` from wait commands.
- Uniform interface reduces the number of special cases agents must handle.
