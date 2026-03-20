import direct_exec_client


COMMAND_GROUPS = (
    (
        "Primary Execution",
        (
            "exec",
        ),
    ),
    (
        "Supporting Observation",
        (
            "wait-for-exec",
            "wait-for-result-marker",
            "wait-for-log-pattern",
            "wait-until-ready",
        ),
    ),
        (
            "Secondary / Troubleshooting",
            (
                "get-log-source",
                "get-blocker-state",
                "resolve-blocker",
                "ensure-stopped",
            ),
        ),
)

COMMANDS = tuple(command for _, commands in COMMAND_GROUPS for command in commands)

EXIT_NO_OBSERVATION_TARGET = 15
EXIT_NOT_STOPPED = 16
EXIT_UNITY_START_FAILED = 20
EXIT_UNITY_NOT_READY = 21

WORKFLOW_IDS = (
    "exec-and-wait-for-result-marker",
    "recover-exec-by-request-id",
    "request-editor-exit-via-exec",
)


def _join_sections(sections):
    return "\n\n".join(section.rstrip() for section in sections if section).rstrip() + "\n"


def _bullet_lines(items):
    return "\n".join("- {}".format(item) for item in items)


TOP_LEVEL_COMMANDS = {
    "wait-until-ready": "prepare a project or direct service until Unity is ready. See `wait-until-ready --help`.",
    "wait-for-log-pattern": "observe logs until a regular-expression pattern appears. See `wait-for-log-pattern --help`.",
    "wait-for-exec": "continue waiting on an accepted exec request by `request_id`. See `wait-for-exec --help`.",
    "wait-for-result-marker": "wait for the standard single-line JSON result marker emitted by a long-running script. See `wait-for-result-marker --help`.",
    "get-log-source": "report the observable Unity log source for the selected target. See `get-log-source --help`.",
    "get-blocker-state": "report whether a supported Unity modal blocker is currently detected for the target project. See `get-blocker-state --help`.",
    "resolve-blocker": "dismiss a supported Unity modal blocker for the target project with an explicit action. See `resolve-blocker --help`.",
    "exec": "run JavaScript against a project or direct service; primary entry for script execution. See `exec --help`.",
    "ensure-stopped": "check or force a stopped state; not the recommended graceful-exit path. See `ensure-stopped --help`.",
}

RECOMMENDED_PATH = (
    "For normal project-scoped work, start with `exec --project-path ...`.",
    "If `exec` returns `running`, continue with `wait-for-exec --request-id ...` or the script-specific observation path you designed.",
    "Use `wait-for-result-marker` after `exec` only when the script deliberately exposes a `correlation_id` workflow.",
    "If you need log-based verification, continue with `wait-for-log-pattern`.",
    "Use `wait-until-ready` when you specifically need readiness recovery before or between `exec` steps.",
    "Use `get-blocker-state` when an exec-side timeout or stall might be caused by a supported Unity modal dialog.",
    "Use `resolve-blocker` only when you intentionally want the CLI to dismiss a supported modal blocker; then continue with the original `request_id` if needed.",
    "`get-log-source` and `ensure-stopped` are secondary commands, not the normal first step.",
)

TOP_LEVEL_WORKFLOWS = {
    "exec-and-wait-for-result-marker": "run a script that returns `correlation_id`, capture `log_offset`, then wait for the terminal result marker.",
    "recover-exec-by-request-id": "recover an accepted exec request by reusing or waiting on the same `request_id` after `running` or ambiguity.",
    "request-editor-exit-via-exec": "request a normal Unity Editor exit through `exec` instead of using `ensure-stopped`.",
}


COMMAND_HELP = {
    "wait-until-ready": {
        "quick_start": [
            "Supporting readiness command for cases where you explicitly need Unity ready before or between `exec` steps.",
            "`unity-puer-exec wait-until-ready --project-path X:/project`",
            "For normal project-scoped work, start with `unity-puer-exec exec --project-path X:/project --file X:/script.js` instead of using this as the default first step.",
        ],
        "related_workflows": (),
        "args": {
            "Arguments": [
                "`--project-path <path>`: select a Unity project and allow Unity launch when needed.",
                "`--base-url <url>`: target an already-known direct service instead of a project.",
                "`--unity-exe-path <path>`: override the Unity executable for project-scoped startup only.",
                "`--unity-log-path <path>`: explicit non-default Unity Editor log path for pre-session project-scoped startup and observation.",
                "`--ready-timeout-seconds <seconds>`: total time allowed for readiness.",
                "`--activity-timeout-seconds <seconds>`: how long readiness may stay idle before stalling.",
                "`--health-timeout-seconds <seconds>`: timeout for each health probe.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--project-path` is the normal choice when you want the CLI to prepare Unity for a project.",
                "`--base-url` is for a direct service you already know how to reach.",
                "`--unity-exe-path` is only valid with `--project-path`.",
            ],
            "Timeout Rules": [
                "All timeout values must be positive numbers.",
                "`--ready-timeout-seconds` bounds the whole readiness wait.",
                "`--activity-timeout-seconds` and `--health-timeout-seconds` refine how readiness stalls are detected.",
            ],
        },
        "status": {
            "success": [
                "`completed`: Unity is ready and `result.status` is `recovered`.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("launch_conflict", EXIT_UNITY_START_FAILED, "project-scoped launch ownership could not be established safely, so the CLI refused a competing launch."),
                ("unity_start_failed", EXIT_UNITY_START_FAILED, "Unity could not be launched for the selected project."),
                ("unity_stalled", EXIT_UNITY_NOT_READY, "readiness stopped making progress before becoming usable."),
                ("unity_not_ready", EXIT_UNITY_NOT_READY, "Unity did not become ready before the readiness budget expired."),
                ("failed", 1, "an unexpected command failure happened outside the expected machine states."),
            ],
        },
    },
    "wait-for-log-pattern": {
        "quick_start": [
            "Supporting observation command for log-based verification after or alongside `exec`.",
            "`unity-puer-exec wait-for-log-pattern --project-path X:/project --pattern \"\\\\[Build\\\\] done\"`",
            "Use this when task success is best verified through Unity log output; the pattern is a regular expression, not a literal string.",
        ],
        "related_workflows": ("exec-and-wait-for-result-marker",),
        "args": {
            "Arguments": [
                "`--project-path <path>`: observe a project's Unity log source.",
                "`--base-url <url>`: observe through a direct service target.",
                "`--unity-log-path <path>`: explicit non-default Unity Editor log path for pre-session project-scoped observation.",
                "`--pattern <regex>`: required regular expression to wait for.",
                "`--start-offset <offset>`: optional log offset from which to begin scanning.",
                "`--expected-session-marker <marker>`: optional same-session guard for observation.",
                "`--extract-group <n>`: return the matched text for capture group `n`.",
                "`--extract-json-group <n>`: parse capture group `n` as JSON and return the parsed object.",
                "`--timeout-seconds <seconds>`: total wait budget for the requested pattern.",
                "`--activity-timeout-seconds <seconds>`: how long observation may stay idle before stalling.",
                "`--health-timeout-seconds <seconds>`: timeout for each health probe.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--project-path` is the normal choice when the CLI should locate observation from a project.",
                "`--base-url` is for a direct service that is already known.",
                "Before a project-scoped session has produced `session_marker`, pass the same `--unity-log-path` on log-related commands when you intentionally avoid the default log location.",
            ],
            "Timeout Rules": [
                "All timeout values must be positive numbers.",
                "`--timeout-seconds` bounds the observation wait itself.",
                "Invalid regex input is a CLI usage error before any observation starts.",
                "`--extract-group` and `--extract-json-group` are mutually exclusive.",
            ],
        },
        "status": {
            "success": [
                "`completed`: the pattern was matched and `result.status` is `log_pattern_matched`.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("no_observation_target", EXIT_NO_OBSERVATION_TARGET, "no eligible Unity log source could be observed for the selected target."),
                ("unity_stalled", EXIT_UNITY_NOT_READY, "observation lost forward progress before the pattern appeared."),
                ("unity_not_ready", EXIT_UNITY_NOT_READY, "the observed target stopped being ready while waiting."),
                ("failed", 1, "the regex was invalid or another unexpected command failure occurred."),
            ],
        },
    },
    "get-log-source": {
        "quick_start": [
            "Secondary troubleshooting command for inspecting the observable Unity log source.",
            "`unity-puer-exec get-log-source --project-path X:/project`",
            "This is not part of the normal project-scoped execution or verification path.",
        ],
        "related_workflows": (),
        "args": {
            "Arguments": [
                "`--project-path <path>`: locate the log source for a Unity project.",
                "`--base-url <url>`: report the log source for a direct service target.",
                "`--unity-log-path <path>`: explicit non-default Unity Editor log path for pre-session project-scoped discovery.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--project-path` is the normal choice when the CLI should discover the target from project context.",
                "`--base-url` is for a direct service that is already known.",
            ],
        },
        "status": {
            "success": [
                "`completed`: a log source is available and `result.status` is `log_source_available`.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("no_observation_target", EXIT_NO_OBSERVATION_TARGET, "no eligible Unity log source could be resolved for the selected target."),
                ("failed", 1, "an unexpected command failure occurred while resolving the observation target."),
            ],
        },
    },
    "get-blocker-state": {
        "quick_start": [
            "Secondary troubleshooting command for confirming whether a supported Unity modal blocker is currently open for the selected project.",
            "`unity-puer-exec get-blocker-state --project-path X:/project`",
            "Use this after an exec-side timeout or stall when you need to distinguish a supported save-scene modal dialog from a generic timeout.",
        ],
        "related_workflows": ("recover-exec-by-request-id",),
        "args": {
            "Arguments": [
                "`--project-path <path>`: inspect the Unity Editor associated with a project for a supported modal blocker.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Selector Rules": [
                "`--project-path` is the only supported selector for this command.",
                "The command is intended for project-scoped Editor troubleshooting, not direct-service or packaged-app targets.",
            ],
        },
        "status": {
            "success": [
                "`completed`: blocker inspection finished; `result.status` is either `no_blocker` or `modal_blocked`.",
            ],
            "failure": [
                ("failed", 1, "an unexpected blocker-query failure occurred."),
            ],
        },
    },
    "resolve-blocker": {
        "quick_start": [
            "Secondary troubleshooting command for explicitly dismissing a supported Unity modal blocker.",
            "`unity-puer-exec resolve-blocker --project-path X:/project --action cancel`",
            "Use this only after you have determined that a supported save-scene blocker is present and machine-issued cancel is acceptable.",
        ],
        "related_workflows": ("recover-exec-by-request-id",),
        "args": {
            "Arguments": [
                "`--project-path <path>`: select the Unity project whose current supported modal blocker should be resolved.",
                "`--action cancel`: dismiss the supported blocker with the dialog's cancel path.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Selector Rules": [
                "`--project-path` is required for this command.",
                "`--base-url` is intentionally unsupported in the first version.",
                "The command is Windows-only and only applies to the supported save-scene blocker types.",
            ],
            "Timeout Rules": [
                "Resolution uses an internal fixed confirmation timeout after clicking cancel; callers do not configure it.",
            ],
        },
        "status": {
            "success": [
                "`completed`: blocker resolution succeeded and `result.status` is `resolved`.",
            ],
            "failure": [
                ("no_supported_blocker", 1, "no supported blocker was currently detected, so the CLI did not interact with any window."),
                ("resolution_failed", 1, "a supported blocker was detected but the cancel interaction could not be completed safely or confirmed."),
                ("unsupported_operation", 1, "the command requires Windows plus `--project-path` in the first version."),
                ("failed", 1, "an unexpected resolution failure occurred."),
            ],
        },
    },
    "exec": {
        "quick_start": [
            "Normal first command for project-scoped work and the primary script execution entry point.",
            "`unity-puer-exec exec --project-path X:/project --file X:/script.js`",
            "`unity-puer-exec exec --project-path X:/project --file X:/script.js --request-id RID`",
            "`unity-puer-exec exec --project-path X:/project --stdin < script.js`",
            "With `--project-path`, `exec` may launch or recover Unity for the project, so you do not need `wait-until-ready` as the default first step.",
        ],
        "related_workflows": (
            "recover-exec-by-request-id",
            "exec-and-wait-for-result-marker",
            "request-editor-exit-via-exec",
        ),
        "args": {
            "Arguments": [
                "`--project-path <path>`: select a Unity project and allow Unity launch when needed.",
                "`--base-url <url>`: target an already-known direct service instead of a project.",
                "`--unity-exe-path <path>`: override the Unity executable for project-scoped startup only.",
                "`--unity-log-path <path>`: explicit non-default Unity Editor log path for project-scoped startup before `session_marker` exists.",
                "`--wait-timeout-ms <ms>`: how long to wait before returning the current execution state.",
                "`--request-id <id>`: optional caller-owned exec identity for recovery or idempotent replay; omitted values are generated automatically.",
                "`--include-log-offset`: include top-level observation `log_offset` in the response for later result-marker waiting.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
                "`--file <path>`: preferred script input for multi-line or AI-generated scripts.",
                "`--stdin`: read script content from standard input.",
                "`--code <inline-js>`: inline module-shaped source; compatibility path with quoting and multiline drawbacks.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--project-path` is the normal choice when the CLI should prepare Unity for the project before execution.",
                "`--base-url` is for a direct service that is already known.",
                "`--unity-exe-path` is only valid with `--project-path`.",
                "Use exactly one script source: `--file`, `--stdin`, or `--code`.",
                "Script input must provide `export default function (ctx) { ... }` as the entry shape.",
            ],
            "Timeout Rules": [
                "`--wait-timeout-ms` must be a positive integer.",
                "The command may return `running` when the wait budget ends before the request finishes.",
                "Reusing the same `--request-id` with equivalent execution content is recovery, not a duplicate execution attempt.",
                "The default-exported entry function must return an immediate JSON-serializable value; Promise return values are rejected.",
            ],
        },
        "status": {
            "success": [
                "`completed`: the script finished; the accepted response includes `request_id`, and the default-exported entry function's immediate return value is in `result`.",
                "`running`: the request is still active; continue with `wait-for-exec --request-id ...` or the script's own observation workflow.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("busy", direct_exec_client.EXIT_BUSY, "a different top-level exec request is already active, so the service refused to queue a new one."),
                ("modal_blocked", direct_exec_client.EXIT_MODAL_BLOCKED, "a supported Unity modal dialog is blocking exec progress; inspect `blocker.type` and keep the same `request_id` for follow-up."),
                ("not_available", direct_exec_client.EXIT_NOT_AVAILABLE, "the direct execution target could not be reached."),
                ("request_id_conflict", direct_exec_client.EXIT_REQUEST_ID_CONFLICT, "the provided `request_id` was already associated with different execution content."),
                ("launch_conflict", EXIT_UNITY_START_FAILED, "project-scoped launch ownership could not be established safely, so execution did not start a competing Unity launch."),
                ("unity_start_failed", EXIT_UNITY_START_FAILED, "Unity could not be launched for the selected project."),
                ("unity_stalled", EXIT_UNITY_NOT_READY, "readiness stopped making progress before execution could proceed."),
                ("unity_not_ready", EXIT_UNITY_NOT_READY, "Unity did not become ready before execution could proceed."),
                ("failed", 1, "execution failed unexpectedly, the module entry shape was invalid, or Promise return values are rejected because only immediate JSON-serializable results are supported."),
            ],
        },
    },
    "wait-for-exec": {
        "quick_start": [
            "Preferred follow-up when you already know an accepted exec `request_id` and want to continue waiting without resubmitting script content.",
            "`unity-puer-exec wait-for-exec --project-path X:/project --request-id RID`",
            "Use this after `exec` returns `running`, or after an ambiguous timeout when you intentionally want recovery with the same `request_id`.",
        ],
        "related_workflows": ("recover-exec-by-request-id",),
        "args": {
            "Arguments": [
                "`--project-path <path>`: select a Unity project and allow Unity launch when needed.",
                "`--base-url <url>`: target an already-known direct service instead of a project.",
                "`--unity-exe-path <path>`: override the Unity executable for project-scoped startup only.",
                "`--unity-log-path <path>`: explicit non-default Unity Editor log path for project-scoped startup before `session_marker` exists.",
                "`--request-id <id>`: required accepted exec identity to continue waiting on.",
                "`--wait-timeout-ms <ms>`: how long to wait before returning the current request state again.",
                "`--include-log-offset`: include top-level observation `log_offset` in the response.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--project-path` is the normal choice when the CLI should prepare Unity for the project before waiting.",
                "`--base-url` is for a direct service that is already known.",
                "`--unity-exe-path` is only valid with `--project-path`.",
            ],
            "Timeout Rules": [
                "`--wait-timeout-ms` must be a positive integer.",
                "`missing` means the addressed service currently has no recoverable record for that `request_id`.",
            ],
        },
        "status": {
            "success": [
                "`completed`: the request finished and any immediate entry return value is in `result`.",
                "`running`: the request is still active and can be waited on again with the same `request_id`.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("modal_blocked", direct_exec_client.EXIT_MODAL_BLOCKED, "a supported Unity modal dialog is blocking the accepted exec request; inspect `blocker.type` and avoid starting a fresh request."),
                ("missing", direct_exec_client.EXIT_MISSING, "the addressed service has no recoverable record for that `request_id`."),
                ("not_available", direct_exec_client.EXIT_NOT_AVAILABLE, "the direct execution target could not be reached."),
                ("launch_conflict", EXIT_UNITY_START_FAILED, "project-scoped launch ownership could not be established safely, so the CLI refused a competing launch."),
                ("unity_start_failed", EXIT_UNITY_START_FAILED, "Unity could not be launched for the selected project."),
                ("unity_stalled", EXIT_UNITY_NOT_READY, "readiness stopped making progress before waiting could proceed."),
                ("unity_not_ready", EXIT_UNITY_NOT_READY, "Unity did not become ready before waiting could proceed."),
                ("failed", 1, "an unexpected wait-for-exec failure occurred."),
            ],
        },
    },
    "wait-for-result-marker": {
        "quick_start": [
            "Normal follow-up when `exec` returns `running` for a long-running workflow.",
            "`unity-puer-exec wait-for-result-marker --project-path X:/project --correlation-id ID --start-offset 12345`",
            "Use the `correlation_id` from the script workflow and the `log_offset` returned by `exec --include-log-offset` or `wait-for-exec --include-log-offset`.",
        ],
        "related_workflows": ("exec-and-wait-for-result-marker",),
        "args": {
            "Arguments": [
                "`--project-path <path>` or `--base-url <url>`: select the observation target.",
                "`--unity-log-path <path>`: explicit non-default Unity Editor log path for pre-session project-scoped observation.",
                "`--correlation-id <id>`: required result-marker correlation id to match.",
                "`--start-offset <offset>`: optional starting log offset, typically returned from `exec --include-log-offset`.",
                "`--expected-session-marker <marker>`: optional same-session guard.",
                "`--timeout-seconds <seconds>`: total wait budget for the terminal marker.",
                "`--activity-timeout-seconds <seconds>`: how long observation may stay idle before stalling.",
                "`--health-timeout-seconds <seconds>`: timeout for each health probe.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "Omitting `--expected-session-marker` allows cross-session observation when the log source is still the intended source of truth.",
                "Before a project-scoped session has produced `session_marker`, pass the same `--unity-log-path` on log-related commands when you intentionally avoid the default log location.",
            ],
            "Timeout Rules": [
                "All timeout values must be positive numbers.",
                "The command ignores invalid-JSON marker candidates and markers whose `correlation_id` does not match.",
            ],
        },
        "status": {
            "success": [
                "`completed`: a matching result marker was found and `result.status` is `result_marker_matched`.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("no_observation_target", EXIT_NO_OBSERVATION_TARGET, "no eligible Unity log source could be observed for the selected target."),
                ("session_missing", direct_exec_client.EXIT_SESSION_STATE, "the target no longer exposes the session continuity information needed for safe guarded observation."),
                ("session_stale", direct_exec_client.EXIT_SESSION_STATE, "the target session changed since the expected session marker was recorded."),
                ("unity_stalled", EXIT_UNITY_NOT_READY, "observation lost forward progress before the marker appeared."),
                ("unity_not_ready", EXIT_UNITY_NOT_READY, "the observed target stopped being ready while waiting."),
                ("failed", 1, "another unexpected command failure occurred while waiting for the marker."),
            ],
        },
    },
    "ensure-stopped": {
        "quick_start": [
            "Secondary cleanup or enforcement command for stopped-state control.",
            "`unity-puer-exec ensure-stopped --project-path X:/project --inspect-only`",
            "This is not part of the normal execution or verification workflow; graceful exits should prefer a script request such as `unity-puer-exec exec --project-path X:/project --file X:/exit.js`.",
        ],
        "related_workflows": (),
        "args": {
            "Arguments": [
                "`--project-path <path>`: inspect or stop a project-owned Unity process.",
                "`--base-url <url>`: inspect a direct service target without process control.",
                "`--timeout-seconds <seconds>`: wait budget for stop confirmation.",
                "`--inspect-only`: report whether the target is already stopped without changing it.",
                "`--immediate-kill`: skip graceful waiting and kill immediately; project mode only.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--project-path` is required for process-control modes.",
                "`--base-url` supports inspection only.",
                "`--immediate-kill` is only valid with `--project-path`.",
            ],
            "Timeout Rules": [
                "`--timeout-seconds` must be a positive number.",
                "Without `--inspect-only` or `--immediate-kill`, the command waits up to the timeout before escalating to a kill in project mode.",
            ],
        },
        "status": {
            "success": [
                "`completed`: the target is stopped and `result.status` is `stopped`.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("not_stopped", EXIT_NOT_STOPPED, "the target is still not stopped under the selected stop mode."),
                ("failed", 1, "an unexpected command failure occurred while checking or enforcing the stopped state."),
            ],
        },
    },
}


WORKFLOW_EXAMPLES = {
    "exec-and-wait-for-result-marker": {
        "goal": "Run a long-running script, capture `log_offset`, and wait for the terminal result marker once the script has made the intended `correlation_id` available.",
        "steps": [
            {
                "command": "`unity-puer-exec exec --project-path X:/project --file X:/scripts/do-work.js --wait-timeout-ms 1000 --include-log-offset`",
                "script_body": [
                    "export default function run(ctx) {",
                    "  const correlation_id = ctx.request_id;",
                    "  console.log('[UnityPuerExecResult] ' + JSON.stringify({ correlation_id, status: 'started' }));",
                    "  return { correlation_id };",
                    "}",
                ],
                "observation": "Expected observation: stdout returns machine-readable JSON with `request_id`. If the script finishes within the wait budget, the immediate entry return value is in `result`. If the script is still active, the response may use `status = \"running\"` and still include top-level `log_offset`.",
            },
            (
                "`unity-puer-exec wait-for-result-marker --project-path X:/project --correlation-id ID --start-offset OFFSET`",
                "Expected observation: stdout stays machine-readable and eventually reaches `status = \"completed\"` with `result.status = \"result_marker_matched\"`.",
            ),
        ],
        "notice": [
            "`exec` is allowed to launch or recover Unity when you target a project with `--project-path`.",
            "`--file` is the preferred script input for multi-line or AI-generated scripts.",
            "`running` is an expected machine state, not an error; branch on it and keep observing via result markers.",
            "Do not assume `running` already includes `result.correlation_id`; if you need correlation-aware observation before completion, design the script to expose that id deliberately.",
            "The default-exported entry function returns the immediate `result`; it is not an implicit async completion channel.",
            "Use `log_offset` plus the script-provided `correlation_id` together so observation begins after the originating `exec` request.",
            "If the session has not yet produced `session_marker` and you intentionally use a non-default Unity log file, keep passing the same `--unity-log-path` on the log-related commands in that workflow.",
        ],
    },
    "recover-exec-by-request-id": {
        "goal": "Recover an accepted exec request safely after `running` or an ambiguous timeout without creating a fresh execution attempt.",
        "steps": [
            (
                "`unity-puer-exec exec --project-path X:/project --file X:/scripts/do-work.js --request-id RID --wait-timeout-ms 1000`",
                "Expected observation: stdout may return `completed` immediately, or `running` with the same `request_id`. If transport fails ambiguously, keep the same `request_id` for recovery.",
            ),
            (
                "`unity-puer-exec wait-for-exec --project-path X:/project --request-id RID --wait-timeout-ms 1000`",
                "Expected observation: stdout returns `running`, `completed`, or `failed` for that accepted request without resubmitting the script.",
            ),
        ],
        "notice": [
            "Let the CLI generate `request_id` automatically for normal first attempts; pass `--request-id` explicitly only when you need stable recovery or idempotent replay.",
            "Reusing the same `request_id` with equivalent execution content is recovery. Using a fresh `request_id` starts a new execution attempt.",
            "For side-effecting scripts, do not blindly retry with a fresh `request_id` after an ambiguous timeout.",
            "`request_id` tracks the exec request itself. `correlation_id` remains script-defined metadata for log or marker observation.",
        ],
    },
    "request-editor-exit-via-exec": {
        "goal": "Request a normal Unity Editor exit through a script instead of using stopped-state control.",
        "steps": [
            {
                "command": "`unity-puer-exec exec --project-path X:/project --file X:/scripts/request-exit.js --wait-timeout-ms 1000`",
                "script_body": [
                    "export default function run(ctx) {",
                    "  const EditorApplication = puer.loadType('UnityEditor.EditorApplication');",
                    "  EditorApplication.Exit(0);",
                    "  return { requested: true, request_id: ctx.request_id };",
                    "}",
                ],
                "observation": "Expected observation: stdout reports the execution result for the exit-request script or returns `running` if the request is still in progress.",
            },
        ],
        "notice": [
            "This example assumes Unity is already available for the selected project.",
            "A script such as `EditorApplication.Exit` is a normal exit request, not a guarantee of immediate stopped-state enforcement.",
            "`ensure-stopped` is for stopped-state inspection or enforcement, not the recommended graceful-exit path.",
        ],
    },
}


def render_top_level_help():
    command_group_sections = []
    for title, commands in COMMAND_GROUPS:
        command_group_sections.append(
            "{}\n{}".format(title, _bullet_lines("{}: {}".format(name, TOP_LEVEL_COMMANDS[name]) for name in commands))
        )
    sections = [
        "Overview\nunity-puer-exec is the primary CLI surface for preparing Unity, executing JavaScript, observing long-running work, and checking session state.\nFor normal project-scoped tasks, start with `exec` and add observation commands only when the workflow needs them.\nLegacy aliases remain compatibility shims and are not authoritative command surfaces.",
        "Recommended Path\n{}".format(_bullet_lines(RECOMMENDED_PATH)),
        "Command Groups\n{}".format("\n\n".join(command_group_sections)),
        "Global Selector Rules\n- Use exactly one selector on commands that target a Unity session: `--project-path` or `--base-url`.\n- `--project-path` is the normal choice when the CLI should discover, launch, or recover Unity for a project.\n- `--base-url` is for a direct service you already know how to reach.",
        "Common Workflows\nUse `unity-puer-exec --help-example <example-id>` to view full steps.\n{}".format(
            _bullet_lines("{}: {}".format(workflow_id, TOP_LEVEL_WORKFLOWS[workflow_id]) for workflow_id in WORKFLOW_IDS)
        ),
    ]
    return _join_sections(sections)


def render_command_help(command):
    info = COMMAND_HELP[command]
    sections = [
        "Quick Start\n{}".format(_bullet_lines(info["quick_start"])),
        "More Help\n{}".format(_bullet_lines(["`--help-args`", "`--help-status`"])),
        "Related Workflows\n{}".format(_bullet_lines("`{}`".format(item) for item in info["related_workflows"]))
        if info["related_workflows"]
        else "Related Workflows\n- none",
    ]
    return _join_sections(sections)


def render_command_args_help(command):
    info = COMMAND_HELP[command]["args"]
    sections = []
    for title in ("Arguments", "Selector Rules", "Timeout Rules"):
        items = info.get(title)
        if items:
            sections.append("{}\n{}".format(title, _bullet_lines(items)))
    return _join_sections(sections)


def render_command_status_help(command):
    info = COMMAND_HELP[command]["status"]
    success_lines = ["All success states exit with code `0`."] + list(info["success"])
    failure_lines = [
        "`{}` -> exit {}: {}".format(status, code, meaning)
        for status, code, meaning in info["failure"]
    ]
    sections = [
        "Success Statuses\n{}".format(_bullet_lines(success_lines)),
        "Non-success Statuses\n{}".format(_bullet_lines(failure_lines)),
    ]
    return _join_sections(sections)


def render_workflow_example(example_id):
    info = WORKFLOW_EXAMPLES[example_id]
    steps = []
    for index, step in enumerate(info["steps"], start=1):
        if isinstance(step, dict):
            step_lines = ["{}. {}".format(index, step["command"])]
            script_body = step.get("script_body")
            if script_body:
                step_lines.append("   Example script body:")
                step_lines.extend("     {}".format(line) for line in script_body)
            step_lines.append("   {}".format(step["observation"]))
            steps.append("\n".join(step_lines))
            continue
        command, observation = step
        steps.append("{}. {}\n   {}".format(index, command, observation))
    sections = [
        "Goal\n{}".format(info["goal"]),
        "Steps\n{}".format("\n".join(steps)),
        "What To Notice\n{}".format(_bullet_lines(info["notice"])),
    ]
    return _join_sections(sections)


def available_example_ids():
    return WORKFLOW_IDS
