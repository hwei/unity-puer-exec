## MODIFIED Requirements

### Requirement: exec unity_compile_error responses carry situation and next_steps

When `exec` returns `status: "unity_compile_error"`, the response SHALL include a `situation` string explaining that C# compilation has errors, the script was not executed, and the agent must fix the C# errors before retrying. The response SHALL include `next_steps` with at least two candidates: one for re-running `exec` with `--refresh-before-exec`, and one for `get-compile-errors`.

#### Scenario: exec returns unity_compile_error with guidance

- **WHEN** `exec --project-path ...` returns `status: "unity_compile_error"`
- **THEN** the response includes `situation` explaining that C# compilation errors exist and the script was not executed
- **AND** the response includes `next_steps` with a candidate for `exec` carrying `--refresh-before-exec`
- **AND** the `exec` candidate includes a concrete `argv` with the selector and file when the original request used a file input
- **AND** the response includes a candidate for `get-compile-errors` with a `when` hint

#### Scenario: exec unity_compile_error guidance references structured diagnostics

- **WHEN** `exec` returns `status: "unity_compile_error"`
- **THEN** the `situation` text points callers to structured compile diagnostics such as `compile_errors_total`, `compile_warnings_total`, `compile_messages`, or `get-compile-errors`
- **AND** the `situation` advises the agent to fix the C# errors and recompile
