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

The CLI SHALL maintain a static guidance matrix keyed by `(command, status)` that determines which `next_steps` and `situation` content to include in each response. The matrix SHALL cover every command in the authoritative flat command tree defined by the formal CLI contract, and all documented response statuses for each. The coverage requirement SHALL be expressed against that command tree rather than against a fixed command count, so adding a command extends the obligation automatically instead of leaving a stale number behind.

#### Scenario: Every documented non-success status has a guidance matrix entry

- **WHEN** a command returns any documented non-success status from the formal CLI contract
- **THEN** the guidance matrix provides either `next_steps`, `situation`, or both for that command × status combination

#### Scenario: Coverage follows the command tree

- **WHEN** a command is present in the authoritative flat command tree
- **THEN** the guidance matrix contains entries for that command
- **AND** a command added to the tree without matrix entries is detected rather than silently returning responses with no guidance

#### Scenario: Guidance matrix does not depend on response payload content

- **WHEN** the CLI constructs `next_steps` for a response
- **THEN** the candidates are determined by the command name and status alone
- **AND** the CLI does not inspect script-authored `result` fields to filter or reorder candidates

### Requirement: Compile-message commands carry freshness guidance

Responses from `get-compile-errors` and `get-compile-warnings` SHALL carry guidance covering the freshness hazard these commands are exposed to: compile messages read before a triggered compilation has settled report the previous compilation's results. The guidance SHALL point at the edge-aware compile wait as the way to establish that the messages being read belong to the intended compilation.

#### Scenario: Compile-message response explains the staleness hazard

- **WHEN** `get-compile-errors` or `get-compile-warnings` returns a response carrying guidance
- **THEN** the guidance explains that messages read before a compile settles belong to the previous compilation
- **AND** the candidates include waiting for the compile cycle before reading

#### Scenario: Compile-message commands carry guidance for service-contact statuses

- **WHEN** `get-compile-errors` or `get-compile-warnings` returns a non-success status arising from contacting the control service
- **THEN** the response carries `next_steps`, `situation`, or both, on the same terms as other service-contacting commands

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

### Requirement: Failed exec responses hint at the puer. prefix for bare $typeof/$ref ReferenceErrors

When `exec` or `wait-for-exec` completes with `status = "failed"` and the `error` field is a `ReferenceError` indicating an undefined bare `$typeof` or `$ref` identifier (a script author omitted the `puer.` prefix), the response `situation` text SHALL include a hint suggesting `puer.$typeof` / `puer.$ref`. This inspection SHALL be limited to augmenting `situation` text for this specific error shape; it SHALL NOT alter `next_steps` candidate selection, and SHALL NOT inspect the script-authored `result` field. This is consistent with, and does not reverse, the existing requirement that `next_steps` candidates are determined by command and status alone.

#### Scenario: exec fails on a bare $typeof reference

- **WHEN** an `exec` script throws `ReferenceError: $typeof is not defined`
- **THEN** the response has `ok: false`, `status: "failed"`
- **AND** the `situation` text includes a hint that the script likely meant `puer.$typeof`

#### Scenario: exec fails on a bare $ref reference

- **WHEN** an `exec` script throws `ReferenceError: $ref is not defined`
- **THEN** the response has `ok: false`, `status: "failed"`
- **AND** the `situation` text includes a hint that the script likely meant `puer.$ref`

#### Scenario: wait-for-exec surfaces the same hint for a recovered failure

- **WHEN** `wait-for-exec --request-id ...` recovers a terminal `failed` response whose `error` is `ReferenceError: $typeof is not defined`
- **THEN** the `situation` text includes the same `puer.$typeof` hint as the equivalent direct `exec` failure

#### Scenario: Unrelated failures do not receive the hint

- **WHEN** an `exec` script fails with an error that does not match the bare `$typeof`/`$ref` `ReferenceError` shape (for example, a `TypeError` or an application-authored error mentioning `$typeof` in a longer message)
- **THEN** the `situation` text does not include the `puer.$typeof`/`puer.$ref` hint

#### Scenario: next_steps candidates remain unaffected

- **WHEN** the `puer.$typeof`/`puer.$ref` hint is added to `situation` for a failed response
- **THEN** the response's `next_steps` candidates are identical to what they would be for any other `("exec", "failed")` or `("wait-for-exec", "failed")` response

### Requirement: Version mismatch responses carry reconciliation guidance

The guidance matrix SHALL cover the `version_mismatch` status for every command that can return it. Because the resolution is an installation change rather than another CLI invocation, the response SHALL carry a `situation` explaining which two halves disagree and how they came to differ.

#### Scenario: Bridge mismatch explains the mixed installation

- **WHEN** a command returns `version_mismatch` from the bridge guard
- **THEN** the response includes a `situation` string stating that the CLI executable and the Unity Editor package ship as one release and that the two observed versions indicate a mixed installation

#### Scenario: Package-layout mismatch explains the stale binary

- **WHEN** a command returns `version_mismatch` from the package-layout guard
- **THEN** the response includes a `situation` string stating that the executable does not match the package tree it is installed in

#### Scenario: Unknown-version mismatch explains the unverifiable half

- **WHEN** a command returns `version_mismatch` because a counterpart reported no version
- **THEN** the response includes a `situation` string stating that the counterpart predates version reporting and therefore cannot be verified as compatible

### Requirement: Version mismatch guidance offers only verification follow-ups

The `next_steps` for `version_mismatch` SHALL be limited to actions that help the caller confirm the installation state. They SHALL NOT suggest re-running the failed command, and SHALL NOT reference any bypass mechanism, because neither would produce a trustworthy result.

#### Scenario: Guidance offers a version query

- **WHEN** a `version_mismatch` response includes `next_steps`
- **THEN** the candidates include `--version` for confirming the acting CLI build
- **AND** no candidate re-runs the failed command with the same mismatched pair

#### Scenario: Guidance does not offer a bypass

- **WHEN** a `version_mismatch` response includes `next_steps` or `situation`
- **THEN** neither references a flag, environment variable, or setting that would suppress the guard

### Requirement: Guidance suppression does not hide version mismatch detail

The `--suppress-guidance` flag SHALL continue to omit `next_steps` and `situation`, but SHALL NOT remove the structured version detail from a `version_mismatch` response, because that detail is the machine-readable result rather than advisory guidance.

#### Scenario: Suppressed guidance retains structured detail

- **WHEN** a caller invokes a command with `--suppress-guidance` and the command returns `version_mismatch`
- **THEN** the response omits `next_steps` and `situation`
- **AND** the response retains the guard identity, the CLI version, the observed counterpart version, and the observed location

### Requirement: Usage-failure responses carry guidance toward argument help

Usage-failure statuses SHALL have guidance-matrix coverage. The response SHALL carry a `situation` naming what was rejected, and `next_steps` directing the caller to the argument help for the command that was invoked. The guidance SHALL NOT offer the failed invocation back to the caller as a retry candidate, because re-running an invocation the CLI has already rejected cannot succeed.

#### Scenario: Parse-level failure carries guidance

- **WHEN** a command returns `invalid_arguments`
- **THEN** the response includes a `situation` describing what was rejected
- **AND** `next_steps` includes the invoked command's argument help entry

#### Scenario: Post-parse usage failures carry guidance

- **WHEN** a command returns a usage status raised after parsing, such as `full_text_requires_include` or `address_conflict`
- **THEN** the response includes `situation`, `next_steps`, or both, rather than status and error text alone

#### Scenario: Guidance does not suggest retrying the rejected invocation

- **WHEN** a usage-failure response includes `next_steps`
- **THEN** no candidate re-runs the rejected invocation unchanged

### Requirement: Shell-expansion hint covers the syntax-error form

The existing bare-`puer.`-prefix hint SHALL be extended to the form that shell expansion actually produces. When an `exec` or `wait-for-exec` failure is a syntax error and the invocation supplied inline code through `--code` that carries the signature of a consumed `$` — a member access immediately followed by a call, such as `puer.(` — the response `situation` SHALL include a hint naming shell variable expansion as the likely cause and single quoting or `--file` as the resolution.

The hint SHALL require both conditions together, and SHALL apply only to `--code`, because `--file` and `--stdin` content does not pass through shell interpolation.

#### Scenario: Expanded variable in inline code

- **WHEN** `exec --code` fails with a syntax error and the submitted code contains a member access immediately followed by a call
- **THEN** the response `situation` includes a hint that a shell may have expanded a `$` token
- **AND** the hint names single quoting or `--file` as the resolution

#### Scenario: Ordinary syntax error is not misattributed

- **WHEN** `exec --code` fails with a syntax error and the submitted code carries no expansion signature
- **THEN** no shell-expansion hint is attached

#### Scenario: File and stdin sources are excluded

- **WHEN** an `exec` invocation supplied its script through `--file` or `--stdin` and fails with a syntax error
- **THEN** no shell-expansion hint is attached, regardless of the code's content

#### Scenario: Existing prefix hint is preserved

- **WHEN** a failure reports a bare `$typeof` or `$ref` reference error
- **THEN** the existing missing-`puer.`-prefix hint is still attached

