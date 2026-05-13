# Runtime Guidance

## Purpose

Define the contract for machine-readable follow-up guidance emitted in CLI runtime responses, including multi-candidate action recommendations, situational explanations, suppression control, and the authoritative guidance matrix.

## Requirements

### Requirement: Responses carry multi-candidate next_steps for actionable follow-up

When a CLI command response reaches a status where one or more concrete follow-up commands are appropriate, the response SHALL include a `next_steps` array. Each entry SHALL carry `command` (string) and `when` (string describing when the action is appropriate). Entries MAY carry `argv` (string array) when the CLI has sufficient context to construct a concrete invocation.

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

### Requirement: Responses carry situation for states requiring contextual explanation

When a CLI command response reaches a status where the agent benefits from understanding the current predicament but no concrete next command is the obvious action, the response SHALL include a `situation` string explaining what the status means and what the agent should consider.

#### Scenario: exec not_available includes situation explanation

- **WHEN** `exec --project-path ...` returns `status = "not_available"`
- **THEN** the response includes a `situation` string explaining that the execution target could not be reached and that project-scoped exec already attempted Unity launch/recovery

#### Scenario: resolve-blocker no_supported_blocker includes situation explanation

- **WHEN** `resolve-blocker` returns `status = "no_supported_blocker"`
- **THEN** the response includes a `situation` string explaining that no supported blocker was detected and suggesting re-evaluation

#### Scenario: situation and next_steps may coexist

- **WHEN** a command response benefits from both a situational explanation and concrete follow-up candidates (e.g., `modal_blocked`)
- **THEN** the response MAY include both `situation` and `next_steps`

### Requirement: Guidance covers all commands and statuses via a static matrix

The CLI SHALL maintain a static guidance matrix keyed by `(command, status)` that determines which `next_steps` and `situation` content to include in each response. The matrix SHALL cover all ten commands and all documented response statuses.

#### Scenario: Every documented non-success status has a guidance matrix entry

- **WHEN** a command returns any documented non-success status from the formal CLI contract
- **THEN** the guidance matrix provides either `next_steps`, `situation`, or both for that command × status combination

#### Scenario: Guidance matrix does not depend on response payload content

- **WHEN** the CLI constructs `next_steps` for a response
- **THEN** the candidates are determined by the command name and status alone
- **AND** the CLI does not inspect script-authored `result` fields to filter or reorder candidates

### Requirement: Global --suppress-guidance flag omits all runtime guidance

The CLI SHALL accept a `--suppress-guidance` flag at the global position (before the command name) that suppresses both `next_steps` and `situation` from all command responses.

#### Scenario: Suppress flag removes guidance from response

- **WHEN** a caller invokes `unity-puer-exec --suppress-guidance exec --project-path ...`
- **AND** the response would normally include `next_steps` or `situation`
- **THEN** the response omits both `next_steps` and `situation`

#### Scenario: Suppress flag does not affect other response fields

- **WHEN** `--suppress-guidance` is active
- **THEN** all other response fields (`ok`, `status`, `request_id`, `result`, `log_range`, `diagnostics`, etc.) remain unaffected

### Requirement: --help-status includes situation-level explanations

The per-command `--help-status` output SHALL include a brief situation explanation for each non-success status, so that agents using `--suppress-guidance` can still query status meanings on demand.

#### Scenario: Agent queries help-status and sees situation descriptions

- **WHEN** an agent invokes `unity-puer-exec exec --help-status`
- **THEN** the output lists each non-success status with its exit code, description, and a situation explanation of what the status means and what the agent should consider

#### Scenario: Suppress flag help text references help-status as fallback

- **WHEN** an agent reads help text that describes the `--suppress-guidance` flag
- **THEN** the text mentions that status explanations remain available via `<command> --help-status`

### Requirement: Warning status responses carry a situation explanation

When a CLI command response reaches `status: "warning"`, the response SHALL include a `situation` string that explains the warning is not a failure: the script body executed successfully, but the return value could not be captured. The `situation` SHALL mention that `console.log` with `wait-for-result-marker` is the recommended path for async result observation.

#### Scenario: exec warning response includes situation

- **WHEN** `exec` returns `status: "warning"` with `warning: "async_result_not_supported"`
- **THEN** the response includes a `situation` string explaining that the script body executed but the entry function returned a Promise
- **AND** the `situation` directs the agent to use `console.log` with `wait-for-result-marker` for async result capture

### Requirement: Warning status responses carry next_steps for async result workflows

When a CLI command response reaches `status: "warning"` and the warning relates to async result handling, the response SHALL include `next_steps` entries that guide the agent toward `wait-for-result-marker` and `wait-for-log-pattern` as alternative result-capture workflows.

#### Scenario: exec warning response includes async workflow next_steps

- **WHEN** `exec` returns `status: "warning"` with `warning: "async_result_not_supported"`
- **THEN** the response includes `next_steps` with at least one candidate for `wait-for-result-marker`
- **AND** the `wait-for-result-marker` candidate includes a `when` hint explaining the async result-marker workflow


### Requirement: exec unity_compile_error responses carry situation and next_steps

When `exec` returns `status: "unity_compile_error"`, the response SHALL include a `situation` string explaining that C# compilation has errors, the script was not executed, and the agent should fix the C# errors before retrying. The response SHALL include `next_steps` with at least two candidates: one for re-running `exec` with `--refresh-before-exec`, and one for `get-compile-errors`.

#### Scenario: exec returns unity_compile_error with guidance

- **WHEN** `exec --project-path ...` returns `status: "unity_compile_error"`
- **THEN** the response includes `situation` explaining that C# compilation errors exist and the script was not executed
- **AND** the response includes `next_steps` with a candidate for `exec` carrying `--refresh-before-exec`
- **AND** the `exec` candidate includes a concrete `argv` with the selector and file
- **AND** the response includes a candidate for `get-compile-errors` with a `when` hint

#### Scenario: exec unity_compile_error guidance references compilation counts

- **WHEN** `exec` returns `status: "unity_compile_error"`
- **THEN** the `situation` text references the number of errors and warnings from the response
- **AND** the `situation` advises the agent to fix the C# errors and recompile

### Requirement: wait-for-exec unity_compile_error responses carry guidance

When `wait-for-exec` returns `status: "unity_compile_error"`, the response SHALL include `situation` and `next_steps` consistent with the exec guidance for the same status.

#### Scenario: wait-for-exec returns unity_compile_error with guidance

- **WHEN** `wait-for-exec --project-path ... --request-id R` returns `status: "unity_compile_error"`
- **THEN** the response includes `situation` explaining the compile error condition
- **AND** the response includes `next_steps` with recovery candidates including `exec --refresh-before-exec`

### Requirement: unity_compile_error status appears in --help-status

The `exec --help-status` and `wait-for-exec --help-status` output SHALL list `unity_compile_error` as a non-success status with its exit code (23) and a situation explanation.

#### Scenario: Agent queries exec --help-status and sees unity_compile_error

- **WHEN** an agent invokes `exec --help-status`
- **THEN** `unity_compile_error` is listed with its exit code (23) and a description of what the status means
