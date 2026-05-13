# Runtime Guidance (delta)

## ADDED Requirements

### Requirement: Exec unity_compile_error responses carry situation and next_steps

When `exec` returns `status: "unity_compile_error"`, the response SHALL include a `situation` string explaining that C# compilation has errors, the script was not executed, and the agent should fix the C# errors before retrying. The response SHALL include `next_steps` with at least two candidates: one for re-running `exec` with `--refresh-before-exec`, and one for `get-compile-errors`.

#### Scenario: exec returns unity_compile_error with guidance

- **WHEN** `exec --project-path ...` returns `status: "unity_compile_error"`
- **THEN** the response includes `situation` explaining that C# compilation errors exist and the script was not executed
- **AND** the response includes `next_steps` with a candidate for re-running `exec` with `--refresh-before-exec`
- **AND** the `--refresh-before-exec` candidate includes a concrete `argv` template with the same `--project-path` and `--file` or `--request-id`
- **AND** the response includes a candidate for `get-compile-errors` with a `when` hint

#### Scenario: exec unity_compile_error guidance references compilation counts

- **WHEN** `exec` returns `status: "unity_compile_error"`
- **THEN** the `situation` text references the number of errors and warnings from the response
- **AND** the `situation` advises the agent to fix the C# errors and recompile

### Requirement: Wait-for-exec unity_compile_error responses carry guidance

When `wait-for-exec` returns `status: "unity_compile_error"`, the response SHALL include `situation` and `next_steps` consistent with the exec guidance for the same status.

#### Scenario: wait-for-exec returns unity_compile_error with guidance

- **WHEN** `wait-for-exec --project-path ... --request-id R` returns `status: "unity_compile_error"`
- **THEN** the response includes `situation` explaining the compile error condition
- **AND** the response includes `next_steps` with recovery candidates including `exec --refresh-before-exec`

### Requirement: unity_compile_error status appears in --help-status

The `exec --help-status` and `wait-for-exec --help-status` output SHALL list `unity_compile_error` as a non-success status with its exit code and a situation explanation.

#### Scenario: Agent queries exec --help-status and sees unity_compile_error

- **WHEN** an agent invokes `unity-puer-exec exec --help-status`
- **THEN** `unity_compile_error` is listed with its exit code (23) and a description of what the status means
