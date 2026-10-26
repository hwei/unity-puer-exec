# Spec Delta

## Purpose

Keep the CLI's process-control commands working on a host whose tools write text the interpreter cannot decode, so a localized message never turns a completed stop into an internal error.

## ADDED Requirements

### Requirement: Host-tool output decoding is lossy but never fatal

The CLI SHALL decode the output of host process tools (`tasklist`, `taskkill`) in a way that cannot raise: bytes that are not valid in the interpreter's chosen encoding SHALL be replaced, and the captured stream for a tool invocation SHALL always be text (possibly empty) rather than absent. Diagnostics that echo that text SHALL tolerate an absent stream.

#### Scenario: A localized tool message does not fail the command

- **WHEN** the CLI invokes a host process tool
- **AND** the tool writes its message in the console code page while the interpreter decodes as UTF-8
- **THEN** the invocation completes and the command produces its normal response
- **AND** any echoed tool text carries replacement characters instead of raising a decode error

#### Scenario: An unreadable stream degrades to empty diagnostics

- **WHEN** a captured stream is unavailable after a tool invocation
- **THEN** the response carries empty text for that stream
- **AND** the command does not fail with an internal error

### Requirement: A stop reports the outcome it produced

When the CLI kills a process to reach the stopped state, it SHALL report the state it actually reached. A tool message it could not decode SHALL NOT change that report.

#### Scenario: A completed kill is not reported as an internal failure

- **WHEN** `ensure-closed` or `close_session` kills a live Editor and the process is gone afterwards
- **AND** the tool's output could not be decoded
- **THEN** the command reports the target as stopped
- **AND** it does not report `failure_origin: cli_internal`

#### Scenario: A failed kill still fails

- **WHEN** the kill tool exits non-zero and the process is still running
- **THEN** the command reports the failure with the tool's decoded text
- **AND** the reported state is not `stopped`

### Requirement: Process-state decisions do not read decoded text

Whether a process is running, and which processes are listed, SHALL be decided from parsed structured output and the tool's exit code, never from matching a message string. Replacement characters in a decoded message SHALL NOT change a process-state decision.

#### Scenario: Replacement characters do not change a liveness answer

- **WHEN** a tool's message contains replacement characters
- **THEN** liveness and process-listing results are the same as they would be with a clean decode
- **AND** no caller has to parse that message to reach a decision
