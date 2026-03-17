# Design

## Scope

This change is about diagnostics visibility policy, not about changing the core result-marker workflow.

Likely affected areas:

- `wait-for-log-pattern`
- `wait-for-result-marker`
- readiness and stop commands that currently surface session diagnostics by default

## Design Direction

The default CLI response should contain only the machine-usable contract needed for normal branching. Debug-oriented fields should move behind explicit opt-in controls such as a future `--include-diagnostics` or equivalent command-level debug mode.

Questions to settle in this change:

- which commands still need lightweight default diagnostics, if any
- whether `session.diagnostics` should remain in default session payloads
- whether opt-in diagnostics should be standardized across commands

## Out of Scope

- redesigning exit codes
- changing the result-marker protocol itself
- adding new long-running workflow commands
