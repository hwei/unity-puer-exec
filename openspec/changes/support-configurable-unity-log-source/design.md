# Design

## Goals

- allow CLI observation commands to use the actual Unity log source even when it is not the platform default path
- allow launch-driven workflows to opt into a custom Unity log path
- keep the default path as a fallback, not the only supported source

## Non-Goals

- changing the current result-marker workflow
- solving the current `log_offset` bug in this change; that work remains tracked separately

## Preferred Direction

Observation should prefer a Unity-provided log path when one is available and fall back to the current default path only when no better source exists. This keeps current behavior working while allowing non-default installations and explicit launch-time overrides.

## Candidate Contract Shape

### Observation

- `get-log-source` should report the effective observable log source, not just the guessed default path
- project-bound observation flows should prefer a Unity-provided log path when the selected target can provide one
- CLI should still retain a default-path fallback so observation can work before Unity becomes fully ready

### Launch

When `unity-puer-exec` launches Unity itself, the launch path should support an explicit log-path override. The final argument name can be decided during implementation, but the workflow should allow:

- caller requests a custom Unity log file path
- Unity is launched with that log-path override
- subsequent observation commands use the same effective path

## Validation

Host validation should prove at least:

- default-path observation still works
- a non-default log path can be observed when Unity exposes or is launched with that path
- launch-driven sessions can align `wait-for-log-pattern` and `wait-for-result-marker` with the effective log source
