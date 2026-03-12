# 0007 Formal CLI Contract

- Date: 2026-03-12
- Status: accepted

## Decision

The first formal CLI contract is a single primary entry:

- `unity-puer-exec`

The formal command tree is flat under that entry:

- `unity-puer-exec ensure-ready`
- `unity-puer-exec wait-until-recovered`
- `unity-puer-exec wait-for-log-pattern`
- `unity-puer-exec exec`
- `unity-puer-exec get-result`

`unity-puer-session` is transitional. During migration it may remain as a compatibility alias for the readiness-oriented commands, but the authoritative contract, help surface, and repository documentation must converge on `unity-puer-exec`. No new product capability should be introduced under `unity-puer-session`.

## Command Roles

### `ensure-ready`

Purpose:

- ensure a Unity session is reachable at the target base URL
- attach to an already-ready service, wait for an existing Unity process to become ready, or launch Unity if needed

Formal inputs:

- `--project-path`
- `--base-url`
- `--unity-exe-path`
- `--ready-timeout-seconds`
- `--activity-timeout-seconds`
- `--health-timeout-seconds`
- `--keep-unity`

Success result:

- `result.status = "ready"`

### `wait-until-recovered`

Purpose:

- wait for a previously reachable but not yet stable Unity session to recover enough for normal command use

Formal inputs:

- `--project-path`
- `--base-url`
- `--unity-exe-path`
- `--timeout-seconds`
- `--activity-timeout-seconds`
- `--health-timeout-seconds`
- `--keep-unity`

Success result:

- `result.status = "recovered"`

### `wait-for-log-pattern`

Purpose:

- wait until the Unity editor log shows a caller-specified pattern

Formal inputs:

- `--project-path`
- `--base-url`
- `--unity-exe-path`
- `--pattern`
- `--timeout-seconds`
- `--activity-timeout-seconds`
- `--health-timeout-seconds`
- `--keep-unity`

Success result:

- `result.status = "log_pattern_matched"`

### `exec`

Purpose:

- send JavaScript to the Unity-side execution service at the target base URL
- either complete immediately or return a running job that can later be polled

Formal inputs:

- `--base-url`
- exactly one script input source
- `--wait-timeout-ms`

Formal script input sources:

- `--file <path>` reads UTF-8 JavaScript from a file
- `--stdin` reads JavaScript from standard input
- `--code <inline-js>` is transitional compatibility only and should not be the recommended path in product help

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

Success result:

- `status = "completed"`

Expected non-success machine states:

- `status = "running"`
- `status = "compiling"`
- `status = "missing"`
- `status = "not_available"`

## Workflow Boundary

The formal boundary between readiness and execution is explicit:

- `ensure-ready`, `wait-until-recovered`, and `wait-for-log-pattern` are Unity-session management commands
- `exec` and `get-result` are execution-service commands
- `exec` does not implicitly launch Unity, resolve a project path, or wait for recovery

Normative workflow:

1. Use `ensure-ready` before the first execution attempt for a target project or base URL.
2. If Unity is known to be compiling, reloading, or otherwise unstable, use `wait-until-recovered` before retrying `exec`.
3. Use `wait-for-log-pattern` only when a workflow depends on a specific Unity log milestone.
4. Use `exec` for the JavaScript request.
5. If `exec` returns `status = "running"`, use `get-result` with the returned `job_id`.

This decision keeps readiness management explicit because the current product needs to support both direct service use and host-managed Unity startup without hiding costly side effects behind `exec`.

## Parameter Rules

General rules:

- Long-form option names are kebab-case.
- Timeout option names must carry units in the name.
- `--base-url` is command-local in the formal surface. Later implementation should not keep both a top-level and subcommand-level `--base-url`.
- Base URL overrides must not require environment variables.
- Timeout inputs in the formal surface must be positive values. Later implementation should reject zero or negative timeout values as usage errors instead of relying on incidental runtime behavior.

Project path resolution remains:

1. explicit `--project-path`
2. `UNITY_PROJECT_PATH` from the process environment
3. repository-local `.env`
4. current working directory

Readiness-oriented commands own project and launcher inputs:

- `--project-path`
- `--unity-exe-path`
- `--keep-unity`

Execution-oriented commands do not own those inputs in the formal surface. They address an already chosen `--base-url`.

`--wait-timeout-ms` remains the execution-service wait control because it matches the current HTTP payload contract.

`--ready-timeout-seconds` remains specific to `ensure-ready`.

`--timeout-seconds` remains the waiting horizon for `wait-until-recovered` and `wait-for-log-pattern`.

## Output Contract

All formal command results must be machine-readable JSON.

Structured command results belong on stdout for:

- success
- expected non-success machine states that an agent can handle programmatically

stderr is reserved for:

- unstructured CLI usage text from the argument parser
- unexpected process-level diagnostics that are not the authoritative machine payload

Later implementation work must converge both current entrypoints on one stdout-first JSON contract.

### Readiness-Oriented Payload Shape

`ensure-ready`, `wait-until-recovered`, and `wait-for-log-pattern` must emit a JSON object with:

- `ok`
- `status`
- `operation`
- `session`
- `result`
- optional `cleanup`
- optional `error`

Success shape:

- `ok = true`
- `status = "completed"`
- `operation` equals the invoked command name
- `session` uses the current `UnitySession.to_payload()` shape as the baseline:
  - `owner`
  - `launched`
  - `base_url`
  - `project_path`
  - `diagnostics`
  - optional `unity_pid`
  - optional `unity_exe_path`
- `result.status` is command-specific:
  - `ready`
  - `recovered`
  - `log_pattern_matched`

Stability rules:

- the presence and top-level role of `session`, `result`, and optional `cleanup` are stable
- the listed top-level `session` keys are stable
- nested `session.diagnostics` contents are best-effort diagnostics unless later decisions promote specific keys
- `cleanup.attempted`, `cleanup.kept`, and `cleanup.closed` are stable when `cleanup` is present
- any additional `cleanup` fields such as tool output or extra notes remain best-effort diagnostics

Expected machine-state failure shape:

- `ok = false`
- `status` is one of:
  - `unity_start_failed`
  - `unity_stalled`
  - `unity_not_ready`
- `error` is a human-readable summary
- `session` is included when a session exists
- `cleanup` is included when cleanup was attempted or intentionally skipped

Unexpected failure shape:

- `ok = false`
- `status = "failed"`
- `error` is a human-readable summary
- `session` and `cleanup` follow the same inclusion rules

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
  - `status = "completed"`, `status = "running"`, `status = "compiling"`, `status = "missing"`, or `status = "not_available"`

Unexpected failures use:

- `ok = false`
- `status = "failed"`
- `error`
- optional `stack`

The current `cli.py` behavior that sends `status = "failed"` JSON to stderr is transitional and should be removed by later implementation work.

## Exit Codes

The baseline exit-code model is:

- `0`: completed successfully
- `10`: execution job is still running
- `11`: target is compiling and cannot satisfy the request yet
- `12`: target service is not available
- `13`: requested async job is missing
- `20`: Unity launch failed
- `21`: Unity did not become ready or recovery stalled
- `1`: unexpected command failure
- `2`: CLI usage error from argument parsing

Exit-code meaning is command-specific:

- `10`, `11`, `12`, and `13` apply to execution-service commands
- `20` and `21` apply to readiness-oriented commands

Expected machine states mapped to non-zero codes remain part of the formal surface because an AI agent needs to branch on them without string-matching stderr.

## Help Contract

Top-level `unity-puer-exec --help` must communicate:

- the single-command entry model
- the flat command list
- one typical workflow:
  - run `ensure-ready`
  - run `exec`
  - if the job is still running, run `get-result`
  - if Unity is unstable, use `wait-until-recovered`
  - if a workflow depends on a log milestone, use `wait-for-log-pattern`
- that `exec` expects an already reachable service and does not launch Unity implicitly
- that file or stdin script input is preferred over inline code for multi-line or AI-generated scripts

Per-command `--help` must communicate:

- the command purpose
- required and optional inputs
- timeout semantics
- the most important success statuses
- the expected non-success statuses and exit codes that an agent can branch on
- at least one minimal invocation example

`wait-for-log-pattern --help` must also communicate:

- that `--pattern` is a regular expression, not a literal string
- that matching starts from the command's current observation point rather than replaying the entire historical editor log
- that invalid regex input is a CLI usage error

## Rationale

- A single flat command tree is easier for both humans and agents to discover from `--help`.
- Keeping readiness explicit avoids hiding Unity launch or recovery side effects inside `exec`.
- Preferring stdin or file input avoids shell-escaping fragility for generated JavaScript.
- A stdout-first JSON contract is easier for machine callers than splitting structured payloads across stdout and stderr.
- Preserving the existing capability areas minimizes product churn while still formalizing the contract.

## Consequences

- `T1.4.2` should establish a product-owned CLI baseline that matches this contract direction instead of preserving the current split between `unity-puer-exec` and `unity-puer-session` as equal peers.
- `T1.4.3` should implement the stdout-first machine contract, formal help text, and transitional alias behavior defined here.
- `T1.4.4` should rewrite repository-facing usage docs to point to `unity-puer-exec` help and this decision, not to skill docs.
- `T1.5` may keep evolving the baseline or replace the implementation language, but the replacement must preserve this formal command contract unless a later decision supersedes it.
