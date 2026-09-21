## MODIFIED Requirements

### Requirement: exec unity_compile_error responses carry situation and next_steps

When `exec` returns `status: "unity_compile_error"`, the response SHALL include a `situation` string explaining that C# compilation has errors, the script was not executed, and the agent must fix the C# errors before retrying. The response SHALL include `next_steps` with at least two candidates: one for re-running `exec` after fixing the errors, and one for `get-compile-errors`. The re-run candidate SHALL NOT carry a refresh flag, because fixing a C# error is itself a file write that the automatic refresh observes.

#### Scenario: exec returns unity_compile_error with guidance

- **WHEN** `exec --project-path ...` returns `status: "unity_compile_error"`
- **THEN** the response includes `situation` explaining that C# compilation errors exist and the script was not executed
- **AND** the response includes `next_steps` with a candidate for re-running `exec` once the errors are fixed
- **AND** that candidate states that saving the fix is itself enough to trigger recompilation on the next exec
- **AND** the `exec` candidate includes a concrete `argv` with the selector and file when the original request used a file input
- **AND** the response includes a candidate for `get-compile-errors` with a `when` hint

#### Scenario: exec unity_compile_error guidance references structured diagnostics

- **WHEN** `exec` returns `status: "unity_compile_error"`
- **THEN** the `situation` text points callers to structured compile diagnostics such as `compile_errors_total`, `compile_warnings_total`, `compile_messages`, or `get-compile-errors`
- **AND** the `situation` advises the agent to fix the C# errors and recompile

#### Scenario: Guidance does not direct callers to a removed flag

- **WHEN** any `unity_compile_error` guidance is produced
- **THEN** no `next_steps` candidate carries a refresh flag

### Requirement: wait-for-exec unity_compile_error responses carry guidance

When `wait-for-exec` returns `status: "unity_compile_error"`, the response SHALL include `situation` and `next_steps` consistent with the exec guidance for the same status.

#### Scenario: wait-for-exec returns unity_compile_error with guidance

- **WHEN** `wait-for-exec --project-path ... --request-id R` returns `status: "unity_compile_error"`
- **THEN** the response includes `situation` explaining the compile error condition
- **AND** the response includes `next_steps` with recovery candidates including re-running `exec` after fixing the errors
- **AND** no candidate carries a refresh flag

### Requirement: Responses carry multi-candidate next_steps for actionable follow-up

When a CLI command response reaches a status where one or more concrete follow-up commands are appropriate, the response SHALL include a `next_steps` array. Each entry SHALL carry `command` (string) and `when` (string describing when the action is appropriate). Entries MAY carry `argv` (string array) when the CLI has sufficient context to construct a concrete invocation. An entry SHALL NOT name a flag or command that the current CLI surface does not accept; in particular no entry SHALL carry a flag that has been removed and retained only to emit a usage error.

#### Scenario: exec running response includes multiple follow-up candidates

- **WHEN** `exec --project-path ...` returns `status = "running"`
- **THEN** the response includes `next_steps` with at least three candidates
- **AND** the first candidate has `command = "wait-for-exec"` with a complete `argv`
- **AND** additional candidates include `wait-for-result-marker` and `wait-for-log-pattern` with `when` hints

#### Scenario: next_steps entry with argv provides a directly usable invocation

- **WHEN** a `next_steps` entry includes an `argv` field
- **THEN** the `argv` array forms a complete command-line invocation including the program name, command, selector, and relevant identifiers
- **AND** the agent can execute the `argv` directly without constructing arguments from other response fields

#### Scenario: next_steps entry without argv provides command and guidance only

- **WHEN** a `next_steps` entry omits `argv`
- **THEN** the entry still carries `command` and `when`
- **AND** the agent is expected to construct the invocation from its own task context and the `when` hint

#### Scenario: Response with no actionable follow-up omits next_steps

- **WHEN** a command response reaches a status where no concrete follow-up command is appropriate (e.g., `not_available`, `no_supported_blocker`)
- **THEN** the response SHALL NOT include `next_steps` or SHALL include an empty `next_steps` array

#### Scenario: Guidance references only live surface

- **WHEN** a response carries `next_steps`
- **THEN** every candidate's `argv` consists of commands and flags the current CLI accepts
- **AND** no candidate names a flag retained only to emit a usage error
