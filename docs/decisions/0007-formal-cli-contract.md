# 0007 Formal CLI Contract

- Date: 2026-03-12
- Revised: 2026-03-16
- Status: accepted

## Decision

The formal CLI remains a single primary entry:

- `unity-puer-exec`

The formal command tree is flat under that entry:

- `unity-puer-exec wait-until-ready`
- `unity-puer-exec wait-for-log-pattern`
- `unity-puer-exec get-log-source`
- `unity-puer-exec exec`
- `unity-puer-exec get-result`
- `unity-puer-exec ensure-stopped`

`unity-puer-session` remains transitional only. During migration it may stay as a compatibility alias for older readiness-oriented entrypoints, but the authoritative contract, help surface, and repository documentation converge on `unity-puer-exec`.

## Selector Model

Formal command addressing uses two mutually exclusive selectors:

- `--project-path`
- `--base-url`

Selector rules:

- the two selectors are mutually exclusive
- supplying both is a usage error and should surface `address_conflict` in the machine contract when the command emits structured output
- `--project-path` selects a Unity project and enables project-local discovery
- `--base-url` selects a directly reachable execution service and does not give the CLI ownership over Unity Editor launch

Project path resolution remains:

1. explicit `--project-path`
2. `UNITY_PROJECT_PATH` from the process environment
3. repository-local `.env`
4. current working directory

## Session Discovery

In `--project-path` mode, the normal discovery artifact is:

- `<project>/Temp/UnityPuerExec/session.json`

The minimum stable fields are:

- `base_url`
- `unity_pid`
- `written_at`
- `protocol_version`

Rules:

- `project_path` is not required inside the artifact because the file is already project-scoped
- `written_at` exists for stale-session checks and diagnostics
- additional fields are non-contractual best-effort data unless a later decision promotes them
- the CLI must not trust a discovered endpoint blindly; later implementation should validate reachability before treating the artifact as live

Machine-readable discovery outcomes that remain part of the formal surface include:

- `session_missing`
- `session_stale`

This revision does not introduce an explicit CLI session identity model. Stronger same-session guarantees for direct-service observation are deferred to follow-up work.

## Command Roles

### `wait-until-ready`

Purpose:

- ensure the target is ready for normal execution use
- in `--project-path` mode, discover an existing session, wait for it to become usable, or implicitly prepare Unity as needed
- in `--base-url` mode, confirm readiness of the directly addressed service without taking ownership of Unity launch

Formal inputs:

- exactly one selector:
  - `--project-path`
  - `--base-url`
- `--unity-exe-path` in `--project-path` mode only
- `--ready-timeout-seconds`
- `--activity-timeout-seconds`
- `--health-timeout-seconds`

Success result:

- `result.status = "recovered"`

`wait-until-ready` is a formal top-level command, but it is not a second independent capability model. In help and documentation it should be described as a specialized shortcut over the readiness path that `exec` can use in project-scoped workflows.

### `wait-for-log-pattern`

Purpose:

- wait until the current observable Unity log source matches a caller-specified pattern

Formal inputs:

- exactly one selector:
  - `--project-path`
  - `--base-url`
- `--pattern`
- `--timeout-seconds`
- `--activity-timeout-seconds`

Rules:

- this command is observation-oriented and does not launch Unity
- in `--project-path` mode it observes the current project-scoped log source
- in `--base-url` mode it observes only the current best-effort observable source for that target and does not imply stable server identity across calls

Success result:

- `result.status = "log_pattern_matched"`

Expected non-success observation state:

- `status = "no_observation_target"`

### `get-log-source`

Purpose:

- report the current observable log source for the selected target so an agent can understand what log stream observation commands refer to

Formal inputs:

- exactly one selector:
  - `--project-path`
  - `--base-url`

Success result:

- `result.status = "log_source_available"`

Stable output fields:

- `result.source`
- optional `result.path`

Rules:

- `get-log-source` is used instead of `get-log-path` because future sources may not always be file-backed
- in `--base-url` mode the returned source description is current best-effort information, not a same-server identity guarantee across later calls

Expected non-success observation state:

- `status = "no_observation_target"`

### `exec`

Purpose:

- send JavaScript to the Unity-side execution service
- either complete immediately or return a running job that can later be polled

Formal inputs:

- exactly one selector:
  - `--project-path`
  - `--base-url`
- exactly one script input source
- `--wait-timeout-ms`
- `--unity-exe-path` in `--project-path` mode only

Formal script input sources:

- `--file <path>` reads UTF-8 JavaScript from a file
- `--stdin` reads JavaScript from standard input
- `--code <inline-js>` remains transitional compatibility only and should not be the recommended path in product help

Rules:

- in `--project-path` mode, `exec` may implicitly prepare Unity enough to satisfy the request
- in `--base-url` mode, `exec` targets an already chosen direct service and does not own Unity launch

Success results:

- `status = "completed"`
- `status = "running"`

### `get-result`

Purpose:

- poll a previously returned async job identifier until a result is available or a machine state prevents completion

Formal inputs:

- `--base-url`
- `--job-id`
- `--wait-timeout-ms`

Rules:

- `get-result` does not restart, reprovision, or rediscover Unity
- if the underlying service continuity required by the job is gone, the command must report that machine state instead of silently creating a new session

Success result:

- `status = "completed"`

Expected non-success machine states:

- `status = "running"`
- `status = "compiling"`
- `status = "missing"`
- `status = "not_available"`
- `status = "session_missing"`
- `status = "session_stale"`

### `ensure-stopped`

Purpose:

- guarantee that the selected target is in a stopped state, or report that this cannot be established under the selected mode

Formal inputs:

- exactly one selector:
  - `--project-path`
  - `--base-url`
- optional stop-mode controls:
  - inspect-only
  - timeout-then-kill
  - immediate-kill

Rules:

- in `--project-path` mode, `ensure-stopped` may:
  - inspect whether the target is already stopped
  - wait up to a timeout and then kill
  - kill immediately
- in `--base-url` mode, `ensure-stopped` may inspect state only and must not kill
- graceful shutdown is intentionally out of scope for this command; callers can use `exec` to send a graceful shutdown script when that behavior is desired

Success result:

- `result.status = "stopped"`

Expected non-success machine state:

- `status = "not_stopped"`

## Workflow Boundary

The revised boundary between readiness, execution, observation, and stop control is:

- `wait-until-ready` is the explicit readiness shortcut
- `exec` is the primary work command and may auto-prepare only in project-scoped mode
- `wait-for-log-pattern` and `get-log-source` are observation commands
- `get-result` is continuation of a previously issued async execution and never reprovisions
- `ensure-stopped` is the explicit stopped-state command

Normative agent workflows:

1. If the goal is to do work against a known project, the agent may call `exec --project-path ...` directly and rely on project-scoped readiness preparation.
2. If the goal is only to make a project or service ready before later work, the agent may call `wait-until-ready`.
3. If a workflow depends on log visibility first, the agent may call `get-log-source`, then decide whether to inspect logs directly or use `wait-for-log-pattern`.
4. If `exec` returns `status = "running"`, the agent should call `get-result`.
5. If the goal is to guarantee shutdown of a project-scoped target, the agent should call `ensure-stopped`.

This contract intentionally keeps `wait-until-ready` even though `exec` can cover the same project-scoped readiness path, because the shortcut improves discoverability for agents without creating a second required capability model.

## Parameter Rules

General rules:

- long-form option names are kebab-case
- timeout option names must carry units in the name
- timeout inputs in the formal surface must be positive values
- selector exclusivity is part of the formal surface and should not be left to incidental implementation behavior

Ownership rules:

- `--unity-exe-path` belongs only to project-scoped commands that may prepare Unity
- `--keep-unity` leaves the formal contract in this revision
- later implementation may keep a temporary compatibility path for `--keep-unity`, but help and contract should no longer treat it as authoritative

Observation rules:

- `wait-for-log-pattern --help` must state that `--pattern` is a regular expression, not a literal string
- matching begins from the command's current observation point rather than replaying the entire historical editor log
- invalid regex input is a CLI usage error

## Output Contract

All formal command results must be machine-readable JSON.

Structured command results belong on stdout for:

- success
- expected non-success machine states that an agent can branch on programmatically

stderr is reserved for:

- unstructured CLI usage text from the argument parser
- unexpected process-level diagnostics that are not the authoritative machine payload

Later implementation work must converge current entrypoints on one stdout-first JSON contract.

### Management And Observation Payload Shape

`wait-until-ready`, `wait-for-log-pattern`, `get-log-source`, and `ensure-stopped` must emit a JSON object with:

- `ok`
- `status`
- `operation`
- optional `session`
- optional `result`
- optional `error`

Success shape:

- `ok = true`
- `status = "completed"`
- `operation` equals the invoked command name
- `session` is included when a concrete session or target description exists
- `result.status` is command-specific:
  - `recovered`
  - `log_pattern_matched`
  - `log_source_available`
  - `stopped`

Stability rules:

- the presence and top-level role of `session`, `result`, and optional `error` are stable
- top-level `session` keys needed for routing remain stable only when promoted explicitly by later decisions
- nested diagnostics remain best-effort unless later decisions promote specific keys
- for `get-log-source`, `result.source` is stable and `result.path` is optional

Expected non-success machine-state shape:

- `ok = false`
- `status` is one of:
  - `session_missing`
  - `session_stale`
  - `address_conflict`
  - `no_observation_target`
  - `not_stopped`
  - `unity_start_failed`
  - `unity_stalled`
  - `unity_not_ready`
- `error` is a human-readable summary
- `session` is included when available

Unexpected failure shape:

- `ok = false`
- `status = "failed"`
- `error` is a human-readable summary

### Execution Payload Shape

`exec` and `get-result` must emit a JSON object with:

- `ok`
- `status`
- optional `job_id`
- optional `result`
- optional `spawn_job_ids`
- optional `error`
- optional `stack`

Stability rules:

- `ok` and `status` are always stable
- `job_id` is stable when the command refers to a concrete job
- `result` is stable only as an optional container for host-returned execution output; its nested shape remains owned by the Unity-side execution protocol
- `spawn_job_ids` is optional and stable only as a list of additional async job identifiers when present

Success and expected machine-state payloads remain on stdout:

- `exec`:
  - `status = "completed"` or `status = "running"`
- `get-result`:
  - `status = "completed"`, `status = "running"`, `status = "compiling"`, `status = "missing"`, `status = "not_available"`, `status = "session_missing"`, or `status = "session_stale"`

Unexpected failures use:

- `ok = false`
- `status = "failed"`
- `error`
- optional `stack`

## Exit Codes

The baseline exit-code model is:

- `0`: completed successfully
- `10`: execution job is still running
- `11`: target is compiling and cannot satisfy the request yet
- `12`: target service is not available
- `13`: requested async job is missing
- `14`: session discovery is missing or stale for a non-launching command
- `15`: no eligible observation target exists
- `16`: target is not stopped under `ensure-stopped`
- `20`: Unity launch failed
- `21`: Unity did not become ready or readiness stalled
- `1`: unexpected command failure
- `2`: CLI usage error from argument parsing

Expected machine states mapped to non-zero codes remain part of the formal surface because an AI agent needs to branch on them without string-matching stderr.

## Help Contract

Top-level `unity-puer-exec --help` must communicate:

- the single-command entry model
- the flat command list
- one typical project-scoped workflow:
  - run `exec --project-path ...`
  - if the job is still running, run `get-result`
- one typical readiness-oriented workflow:
  - run `wait-until-ready`
  - then run later work commands as needed
- one typical observation-oriented workflow:
  - run `get-log-source`
  - then run `wait-for-log-pattern` if a workflow depends on a log milestone
- that `wait-until-ready` is a specialized shortcut over the readiness path already used by project-scoped `exec`
- that file or stdin script input is preferred over inline code for multi-line or AI-generated scripts
- that `ensure-stopped` is the stopped-state command and does not promise graceful shutdown

Per-command `--help` must communicate:

- the command purpose
- required and optional inputs
- selector exclusivity rules
- timeout semantics
- the most important success statuses
- the expected non-success statuses and exit codes that an agent can branch on
- at least one minimal invocation example

## Rationale

- A single flat command tree is easier for both humans and agents to discover from `--help`.
- Keeping `wait-until-ready` as a formal top-level command improves discoverability even though project-scoped `exec` can cover the same readiness path.
- Mutually exclusive `--project-path` and `--base-url` selectors produce a clearer model than mixing project discovery and direct service control in the same call.
- Preferring `get-log-source` over `get-log-path` leaves room for non-file-backed observation sources.
- Preferring stdin or file input avoids shell-escaping fragility for generated JavaScript.
- A stdout-first JSON contract is easier for machine callers than splitting structured payloads across stdout and stderr.

## Consequences

- `T1.4.2` should establish a product-owned CLI baseline that matches this revised selector model, command tree, and stopped-state contract.
- `T1.4.3` should implement the stdout-first machine contract, formal help text, and transitional compatibility behavior defined here.
- `T1.4.1.2` should explore whether future CLI revisions need an explicit session identity model for stronger same-session guarantees.
- `T1.4.4` should rewrite repository-facing usage docs to point to `unity-puer-exec` help and this decision, not to skill docs.
- `T1.5` may keep evolving the baseline or replace the implementation language, but the replacement must preserve this formal command contract unless a later decision supersedes it.
