# Design

## Scope

This change is about diagnostics visibility policy, not about changing the core result-marker workflow.

Affected areas:

- `exec`
- `wait-until-ready`
- `wait-for-log-pattern`
- `wait-for-result-marker`
- `get-log-source`
- `ensure-stopped`

## Design Direction

The default CLI response should contain only the machine-usable contract needed for normal branching. Debug-oriented fields should move behind an explicit opt-in control.

This change standardizes diagnostics behavior across all formal commands:

- every formal command supports `--include-diagnostics`
- diagnostics are hidden by default
- diagnostics, when requested, are returned only at top-level `payload.diagnostics`
- `session` and `result` stop carrying diagnostics payloads

## Payload Shape

The stable contract remains:

- top-level machine state fields such as `ok`, `status`, and `operation`
- `session` for stable session facts
- `result` for stable command result data

Debug information moves to:

```json
{
  "ok": true,
  "status": "completed",
  "operation": "wait-for-result-marker",
  "session": { "...": "..." },
  "result": { "...": "..." },
  "diagnostics": { "...": "..." }
}
```

`session.diagnostics` and `result.diagnostics` are removed as default and opt-in shapes. Diagnostics are command-execution metadata, so they belong at top level.

## Command Rules

- `exec` also supports `--include-diagnostics`; it is not exempt from the unified policy.
- default command responses must not require diagnostics for normal branching
- opt-in diagnostics may contain different fields by command, but they share the same top-level placement
- help text should describe diagnostics as debug-oriented, not as part of the ordinary machine contract

## Out of Scope

- redesigning exit codes
- changing the result-marker protocol itself
- adding new long-running workflow commands
