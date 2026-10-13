# Runtime Guidance

## Purpose

Define the contract for machine-readable follow-up guidance emitted in CLI runtime responses, including multi-candidate action recommendations, situational explanations, suppression control, and the authoritative guidance matrix.

## Requirements

### Requirement: Responses carry multi-candidate next_steps for actionable follow-up

When a CLI command response reaches a status where one or more concrete follow-up commands are appropriate, the response SHALL include a `next_steps` array. Each entry SHALL carry `command` (string) and `when` (string describing when the action is appropriate), and MAY carry `argv` (string array) when the CLI has sufficient context to construct a concrete invocation.

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

### Requirement: Guidance references only live CLI surface

An entry SHALL NOT name a flag or command that the current CLI surface does not accept; in particular no entry SHALL carry a flag that has been removed and retained only to emit a usage error.

#### Scenario: Guidance references only live surface

- **WHEN** a response carries `next_steps`
- **THEN** every candidate's `argv` consists of commands and flags the current CLI accepts
- **AND** no candidate names a flag retained only to emit a usage error

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

The CLI SHALL maintain a static guidance matrix keyed by `(command, status)` that determines which `next_steps` and `situation` content to include in each response. The matrix SHALL cover every command in the authoritative flat command tree defined by the formal CLI contract, and all documented response statuses for each.

#### Scenario: Every documented non-success status has a guidance matrix entry

- **WHEN** a command returns any documented non-success status from the formal CLI contract
- **THEN** the guidance matrix provides either `next_steps`, `situation`, or both for that command × status combination

### Requirement: Coverage follows the command tree, not a fixed count

The coverage requirement SHALL be expressed against that command tree rather than against a fixed command count, so adding a command extends the obligation automatically instead of leaving a stale number behind.

#### Scenario: Coverage follows the command tree

- **WHEN** a command is present in the authoritative flat command tree
- **THEN** the guidance matrix contains entries for that command
- **AND** a command added to the tree without matrix entries is detected rather than silently returning responses with no guidance

### Requirement: Candidate selection ignores script-authored result fields

Candidate *selection* (which commands appear, in which order, and whether a `situation` is attached) SHALL be determined by the command name and status alone. The CLI SHALL NOT inspect script-authored `result` fields to filter, reorder, or replace candidates.

#### Scenario: Candidate selection ignores script-authored result fields

- **WHEN** the CLI constructs `next_steps` for a response
- **THEN** the candidates are determined by the command name and status alone
- **AND** the CLI does not inspect script-authored `result` fields to filter or reorder candidates

### Requirement: Argv placeholders fill only from CLI-owned fields

When a selected candidate includes an `argv_template`, the CLI MAY fill placeholder values from CLI-owned response envelope fields (including `log_range`) and from invocation arguments; it SHALL NOT fill placeholders from script-authored `result`.

#### Scenario: Argv values may use CLI-owned envelope fields

- **WHEN** a guidance-matrix candidate carries an `argv_template` that references CLI-owned envelope fields such as `log_range`
- **AND** those fields are present on the response being annotated
- **THEN** the emitted `argv` includes the concrete values from those fields
- **AND** candidate selection for that response remains identical to any other response with the same command and status

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

When `exec` returns `status: "unity_compile_error"`, the response SHALL include a `situation` string explaining that C# compilation has errors, the script was not executed, and the agent must fix the C# errors before retrying. The response SHALL include `next_steps` with at least two candidates: one for re-running `exec` after fixing the errors, and one for `get-compile-errors`.

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

### Requirement: Compile-error re-run candidate carries no refresh flag

The re-run candidate SHALL NOT carry a refresh flag, because fixing a C# error is itself a file write that the automatic refresh observes.

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

### Requirement: unity_compile_error status appears in --help-status

The `exec --help-status` and `wait-for-exec --help-status` output SHALL list `unity_compile_error` as a non-success status with its exit code (23) and a situation explanation.

#### Scenario: Agent queries exec --help-status and sees unity_compile_error

- **WHEN** an agent invokes `exec --help-status`
- **THEN** `unity_compile_error` is listed with its exit code (23) and a description of what the status means

### Requirement: Failed exec responses hint at the puer. prefix for bare $typeof/$ref ReferenceErrors

When `exec` or `wait-for-exec` completes with `status = "failed"` and the `error` field is a `ReferenceError` indicating an undefined bare `$typeof` or `$ref` identifier (a script author omitted the `puer.` prefix), the response `situation` text SHALL include a hint suggesting `puer.$typeof` / `puer.$ref`.

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

### Requirement: The prefix hint does not alter candidate selection

This inspection SHALL be limited to augmenting `situation` text for this specific error shape; it SHALL NOT alter `next_steps` candidate selection, and SHALL NOT inspect the script-authored `result` field. This is consistent with, and does not reverse, the existing requirement that `next_steps` candidates are determined by command and status alone.

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

The existing bare-`puer.`-prefix hint SHALL be extended to the form that shell expansion actually produces. When an `exec` or `wait-for-exec` failure is a syntax error and the invocation supplied inline code through `--code` that carries the signature of a consumed `$` -- a member access immediately followed by a call, such as `puer.(` -- the response `situation` SHALL include a hint naming shell variable expansion as the likely cause and single quoting or `--file` as the resolution.

#### Scenario: Expanded variable in inline code

- **WHEN** `exec --code` fails with a syntax error and the submitted code contains a member access immediately followed by a call
- **THEN** the response `situation` includes a hint that a shell may have expanded a `$` token
- **AND** the hint names single quoting or `--file` as the resolution

#### Scenario: Existing prefix hint is preserved

- **WHEN** a failure reports a bare `$typeof` or `$ref` reference error
- **THEN** the existing missing-`puer.`-prefix hint is still attached

### Requirement: Shell-expansion hint is limited to inline code

The hint SHALL require both conditions together, and SHALL apply only to `--code`, because `--file` and `--stdin` content does not pass through shell interpolation.

#### Scenario: Ordinary syntax error is not misattributed

- **WHEN** `exec --code` fails with a syntax error and the submitted code carries no expansion signature
- **THEN** no shell-expansion hint is attached

#### Scenario: File and stdin sources are excluded

- **WHEN** an `exec` invocation supplied its script through `--file` or `--stdin` and fails with a syntax error
- **THEN** no shell-expansion hint is attached, regardless of the code's content

### Requirement: Success-path observation windows carry an error-sweep follow-up

When `exec`, `wait-for-exec`, or `wait-for-log-pattern` returns `status = "completed"` and the
response carries a CLI-owned `log_range` with both `start` and `end`, the response SHALL include
`next_steps` with a `get-log-briefs` candidate that re-scans that window. When the caller's
selector is one `get-log-briefs` accepts (`--project-path`), the candidate's `argv` SHALL be a
complete invocation using `--range <start>-<end>` built from `log_range.start` and
`log_range.end`, and SHALL include `--levels error,warning`. When the caller used `--base-url`,
`get-log-briefs` has no base-url form, so the candidate SHALL remain present and SHALL omit
`argv` rather than carrying a selector flag the command rejects.

#### Scenario: exec completed offers a copyable error sweep

- **WHEN** `exec` returns `status = "completed"` with `log_range.start` and `log_range.end` present and a project-path selector available
- **THEN** the response includes a `next_steps` entry with `command = "get-log-briefs"`
- **AND** that entry's `argv` includes `--range` with the value `{log_range.start}-{log_range.end}`
- **AND** that entry's `argv` includes `--levels` with the value `error,warning`

#### Scenario: wait-for-exec completed offers the same error sweep

- **WHEN** `wait-for-exec` returns `status = "completed"` with `log_range.start` and `log_range.end` present and a project-path selector available
- **THEN** the response includes a `next_steps` entry with `command = "get-log-briefs"`
- **AND** that entry's `argv` includes the same `--range` and `--levels error,warning` shape as the `exec` completed case

#### Scenario: wait-for-log-pattern completed offers the error sweep and explains the limit of a match

- **WHEN** `wait-for-log-pattern` returns `status = "completed"` with `log_range.start` and `log_range.end` present and a project-path selector available
- **THEN** the response includes a `situation` string stating that a pattern match does not imply the observation window contained no new errors or warnings
- **AND** the response includes a `next_steps` entry with `command = "get-log-briefs"` whose `argv` re-scans that window with `--levels error,warning`

#### Scenario: A base-url completed response keeps the error sweep without argv

- **WHEN** `exec` returns `status = "completed"` with `log_range.start` and `log_range.end` present and a `--base-url` selector
- **THEN** the response includes a `next_steps` entry with `command = "get-log-briefs"`
- **AND** that entry omits `argv`
- **AND** that entry does not name `--base-url`

#### Scenario: Script result does not change the success-path candidates

- **WHEN** `exec` returns `status = "completed"` with two different script-authored `result` values across otherwise identical envelopes
- **THEN** both responses carry the same `next_steps` candidate set for that command and status

### Requirement: Incomplete log_range drops argv but keeps the candidate

Candidate presence is determined by command and status alone, except for a continuation that the addressed service cannot honor: a candidate requiring a record for the addressed `request_id` SHALL be omitted when no such record exists. Apart from that case, missing `log_range` or selector context SHALL cause the entry to omit `argv` while still carrying `command` and `when`, rather than removing the candidate or substituting a different command.

#### Scenario: Incomplete log_range drops argv but keeps the candidate

- **WHEN** one of the covered commands returns `status = "completed"` without both `log_range.start` and `log_range.end`
- **THEN** the `get-log-briefs` candidate is still present with `command` and `when`
- **AND** that candidate omits `argv`

#### Scenario: A missing selector omits argv but keeps the candidate

- **WHEN** a continuation candidate's `argv` cannot be filled because the selector context is
  absent, and the addressed service does hold a record for the request
- **THEN** the candidate is still present with `command` and `when`
- **AND** it omits `argv` rather than being removed or replaced by another command

### Requirement: Blocker guidance suggests the action legal for the reported blocker

The guidance matrix SHALL NOT suggest `resolve-blocker --action cancel` for a blocker type that cancel does not support. For the Safe Mode dialog it SHALL suggest `--action cancel`; for every other reported dialog -- including save-scene dialogs and `unknown_modal_dialog` -- it SHALL suggest the button-targeted form instead.

#### Scenario: Guidance for an unknown dialog suggests a click, not a cancel

- **WHEN** a command response reports `blocker.type = "unknown_modal_dialog"`
- **THEN** any `resolve-blocker` guidance entry suggests `--action click --hwnd --button`
- **AND** no suggested `argv` carries `--action cancel` for that blocker type

#### Scenario: Guidance for Safe Mode still suggests cancel

- **WHEN** a command response reports `blocker.type = "safe_mode_dialog"`
- **THEN** the `resolve-blocker` guidance entry suggests `--action cancel`
- **AND** the entry states that cancel is legal only for Safe Mode

### Requirement: Click guidance carries the blocker-type condition without argv

Because candidate selection is driven by command and status alone, guidance for a blocker-bearing status SHALL carry the `when` condition that lets the caller pick the right form from the reported `blocker.type`, and SHALL NOT emit a concrete `argv` for the click form, since `hwnd` and button label come from the blocker payload rather than from the invocation arguments.

#### Scenario: Click guidance names the payload fields it depends on

- **WHEN** a guidance entry suggests the button-targeted resolution form
- **THEN** its `when` text tells the caller to read `hwnd` and the button label from the reported blocker payload
- **AND** the entry omits `argv` rather than emitting an invocation with placeholder values the CLI cannot fill

### Requirement: Guidance covers button-targeted resolution failure statuses

Candidate selection SHALL remain driven by command name and status alone, so the button-targeted path's failure modes share the existing `resolution_failed` status and are distinguished only by `error`.

#### Scenario: Situation does not depend on the error value

- **WHEN** the CLI builds guidance for a `resolve-blocker` `resolution_failed` response
- **THEN** the selected candidate is the one keyed by command and status alone
- **AND** the CLI does not inspect the `error` field to choose, reorder, or replace that candidate

### Requirement: resolution_failed guidance covers both button-targeted failure modes

The guidance matrix SHALL therefore provide a `situation` explanation for `(resolve-blocker, resolution_failed)` that covers both failure modes: a stale or foreign window handle, and a button label matching no enumerated button. Each explanation SHALL state what the caller should verify before retrying.

#### Scenario: Stale handle failure carries an explanation

- **WHEN** `resolve-blocker` returns `status = "resolution_failed"` with `error = "window_not_found"`
- **THEN** the response includes a `situation` string
- **AND** the `situation` text explains the stale-or-foreign-handle case and directs the caller to re-query blocker state for a current handle

#### Scenario: Unmatched label failure carries an explanation

- **WHEN** `resolve-blocker` returns `status = "resolution_failed"` with `error = "button_not_found"`
- **THEN** the response includes a `situation` string
- **AND** the `situation` text explains the no-matching-button case and directs the caller to re-read the `buttons` array from the blocker payload

### Requirement: Play-mode compile block guidance leads out of play mode

Responses that report a compile blocked by play mode, whether the `exec` warning or the `wait-for-compile` `compile_blocked` outcome, SHALL carry a `situation` saying that the pending change will not compile until the Editor leaves play mode. They SHALL carry `next_steps` that exit play mode, confirm it was exited, and then continue the compile cycle. They SHALL NOT suggest forcing a script compilation while play mode continues.

#### Scenario: Agent receives the exec play-mode warning

- **WHEN** an `exec` response reports `warning: "compile_blocked_by_play_mode"`
- **THEN** its `situation` states that the script ran without the pending change and that compilation waits for play mode to exit
- **AND** its `next_steps` include a step that exits play mode
- **AND** its `next_steps` include a follow-up that waits for the resulting compile cycle

#### Scenario: Agent receives the wait-for-compile block outcome

- **WHEN** `wait-for-compile` returns `result.status: "compile_blocked"`
- **THEN** its `situation` states that the compile cannot start while play mode continues
- **AND** its `next_steps` lead out of play mode before retrying the wait
- **AND** neither field suggests `CompilationPipeline.RequestScriptCompilation()` as the remedy

#### Scenario: The new statuses appear in status help

- **WHEN** an agent reads `exec --help-status` or `wait-for-compile --help-status`
- **THEN** the play-mode compile block is listed with its meaning and its way out

### Requirement: Warning guidance composes all applicable CLI-owned conditions

When a warning response also carries a `compile_blocked` object, the response SHALL carry
`situation` and `next_steps` covering both the warning's own condition and the play-mode
compile block, rather than selecting one. The play-mode exit steps SHALL be present together
with the warning's own follow-up. Composition SHALL key on the CLI-composed `compile_blocked`
object and SHALL NOT read any script-authored `result` field. The single `warning` code SHALL
be unchanged.

#### Scenario: Async warning collides with a play-mode block

- **WHEN** an `exec` response reports `status: "warning"` with `warning: "async_result_not_supported"`
- **AND** the response carries a `compile_blocked` object
- **THEN** its `situation` states both that the entry function returned a Promise and that the pending change will not compile until play mode exits
- **AND** its `next_steps` include a step that exits play mode, a step that confirms play mode was exited, and a follow-up that waits for the compile cycle
- **AND** its `next_steps` preserve the warning's own async follow-up (`wait-for-result-marker`)
- **AND** `warning` remains `async_result_not_supported`

#### Scenario: A warning without a block is unchanged

- **WHEN** a warning response carries no `compile_blocked` object
- **THEN** its `situation` and `next_steps` are the same as before this composition existed

#### Scenario: Composition only adds, never replaces

- **WHEN** a warning response carries a `compile_blocked` object
- **THEN** the guidance candidates for the warning's own condition are still present
- **AND** the play-mode exit candidates are added rather than substituted

### Requirement: A wait-for-exec continuation requires a record, not a template

Whether a response offers `wait-for-exec --request-id` as a continuation SHALL depend on whether the addressed service holds a record for that `request_id`, not on whether the CLI can construct the invocation. When a record exists the candidate SHALL be offered for every selector, omitting `argv` rather than being removed when the selector arguments cannot be filled. When no record exists the CLI SHALL offer no such candidate.

#### Scenario: An accepted base-url request keeps its continuation without argv

- **WHEN** `exec --base-url ...` returns `running` for a request the service accepted
- **THEN** the response includes a `wait-for-exec` candidate with a `when` hint
- **AND** that candidate carries a complete `argv` using the `--base-url` selector when the
  context can fill it
- **AND** it omits `argv` rather than being removed when it cannot

#### Scenario: A request the service never accepted offers no such candidate

- **WHEN** a response describes a request the addressed service holds no record for
- **THEN** the response offers no `wait-for-exec --request-id` candidate
- **AND** any continuation it does offer converges on the script result rather than answering
  `missing`

### Requirement: Continuation candidates carry the selector-appropriate argv

When a continuation candidate names a command that accepts both `--project-path` and
`--base-url`, and the response that carries the candidate is reachable under either selector,
the candidate SHALL carry an `argv` variant for each addressing mode and SHALL emit the variant
matching the selector the caller used. The candidate SHALL NOT omit `argv` when the selector it
was reached through is present and the named command accepts that selector.

#### Scenario: A base-url wait-for-exec continuation carries a base-url argv

- **WHEN** `wait-for-exec --base-url ...` returns `running` for an accepted request
- **THEN** the `wait-for-exec` candidate's `argv` names `--base-url` and the request id
- **AND** it does not name `--project-path`

#### Scenario: A project-path continuation is unchanged

- **WHEN** a converted candidate is reached through `--project-path`
- **THEN** its `argv` names `--project-path` and not `--base-url`

#### Scenario: A project-path-only target keeps its candidate and omits argv

- **WHEN** `exec --base-url ...` returns `completed` with a CLI-owned `log_range`
- **THEN** the `get-log-briefs` candidate is still present with `command` and `when`
- **AND** the candidate omits `argv` rather than naming a selector `get-log-briefs` does not accept
