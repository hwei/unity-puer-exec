## ADDED Requirements

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
