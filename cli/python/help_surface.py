import direct_exec_client


COMMANDS = (
    "wait-until-ready",
    "wait-for-log-pattern",
    "get-log-source",
    "exec",
    "get-result",
    "ensure-stopped",
)

EXIT_NO_OBSERVATION_TARGET = 15
EXIT_NOT_STOPPED = 16
EXIT_UNITY_START_FAILED = 20
EXIT_UNITY_NOT_READY = 21

WORKFLOW_IDS = (
    "cold-start-exec-and-get-result",
    "long-job-and-log-pattern",
    "request-editor-exit-via-exec",
)


def _join_sections(sections):
    return "\n\n".join(section.rstrip() for section in sections if section).rstrip() + "\n"


def _bullet_lines(items):
    return "\n".join("- {}".format(item) for item in items)


TOP_LEVEL_COMMANDS = {
    "wait-until-ready": "prepare a project or direct service until Unity is ready. See `wait-until-ready --help`.",
    "wait-for-log-pattern": "observe logs until a regular-expression pattern appears. See `wait-for-log-pattern --help`.",
    "get-log-source": "report the observable Unity log source for the selected target. See `get-log-source --help`.",
    "exec": "run JavaScript against a project or direct service; primary entry for script execution. See `exec --help`.",
    "get-result": "continue waiting for async execution by using a prior `continuation_token`. See `get-result --help`.",
    "ensure-stopped": "check or force a stopped state; not the recommended graceful-exit path. See `ensure-stopped --help`.",
}

TOP_LEVEL_WORKFLOWS = {
    "cold-start-exec-and-get-result": "start Unity on demand, run a file-based script, then continue a running job with `get-result`.",
    "long-job-and-log-pattern": "register log observation first, start a fake long-running workload, then block until a log milestone appears.",
    "request-editor-exit-via-exec": "request a normal Unity Editor exit through `exec` instead of using `ensure-stopped`.",
}


COMMAND_HELP = {
    "wait-until-ready": {
        "quick_start": [
            "Shortcut for the readiness path already covered by project-scoped `exec`.",
            "`unity-puer-exec wait-until-ready --project-path X:/project`",
            "Equivalent readiness path: `unity-puer-exec exec --project-path X:/project --file X:/script.js`",
        ],
        "related_workflows": (),
        "args": {
            "Arguments": [
                "`--project-path <path>`: select a Unity project and allow Unity launch when needed.",
                "`--base-url <url>`: target an already-known direct service instead of a project.",
                "`--unity-exe-path <path>`: override the Unity executable for project-scoped startup only.",
                "`--ready-timeout-seconds <seconds>`: total time allowed for readiness.",
                "`--activity-timeout-seconds <seconds>`: how long readiness may stay idle before stalling.",
                "`--health-timeout-seconds <seconds>`: timeout for each health probe.",
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
                ("unity_start_failed", EXIT_UNITY_START_FAILED, "Unity could not be launched for the selected project."),
                ("unity_stalled", EXIT_UNITY_NOT_READY, "readiness stopped making progress before becoming usable."),
                ("unity_not_ready", EXIT_UNITY_NOT_READY, "Unity did not become ready before the readiness budget expired."),
                ("failed", 1, "an unexpected command failure happened outside the expected machine states."),
            ],
        },
    },
    "wait-for-log-pattern": {
        "quick_start": [
            "Wait until the selected Unity log emits a regular-expression pattern from the current observation point.",
            "`unity-puer-exec wait-for-log-pattern --project-path X:/project --pattern \"\\\\[Build\\\\] done\"`",
            "The pattern is a regular expression, not a literal string.",
        ],
        "related_workflows": ("long-job-and-log-pattern",),
        "args": {
            "Arguments": [
                "`--project-path <path>`: observe a project's Unity log source.",
                "`--base-url <url>`: observe through a direct service target.",
                "`--pattern <regex>`: required regular expression to wait for.",
                "`--timeout-seconds <seconds>`: total wait budget for the requested pattern.",
                "`--activity-timeout-seconds <seconds>`: how long observation may stay idle before stalling.",
                "`--health-timeout-seconds <seconds>`: timeout for each health probe.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--project-path` is the normal choice when the CLI should locate observation from a project.",
                "`--base-url` is for a direct service that is already known.",
            ],
            "Timeout Rules": [
                "All timeout values must be positive numbers.",
                "`--timeout-seconds` bounds the observation wait itself.",
                "Invalid regex input is a CLI usage error before any observation starts.",
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
            "Report the observable Unity log source for the selected target.",
            "`unity-puer-exec get-log-source --project-path X:/project`",
        ],
        "related_workflows": (),
        "args": {
            "Arguments": [
                "`--project-path <path>`: locate the log source for a Unity project.",
                "`--base-url <url>`: report the log source for a direct service target.",
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
    "exec": {
        "quick_start": [
            "Run JavaScript against a Unity project or direct service; this is the primary script execution entry point.",
            "`unity-puer-exec exec --project-path X:/project --file X:/script.js`",
            "`unity-puer-exec exec --project-path X:/project --stdin < script.js`",
        ],
        "related_workflows": (
            "cold-start-exec-and-get-result",
            "long-job-and-log-pattern",
            "request-editor-exit-via-exec",
        ),
        "args": {
            "Arguments": [
                "`--project-path <path>`: select a Unity project and allow Unity launch when needed.",
                "`--base-url <url>`: target an already-known direct service instead of a project.",
                "`--unity-exe-path <path>`: override the Unity executable for project-scoped startup only.",
                "`--wait-timeout-ms <ms>`: how long to wait before returning the current execution state.",
                "`--file <path>`: preferred script input for multi-line or AI-generated scripts.",
                "`--stdin`: read script content from standard input.",
                "`--code <inline-js>`: inline script source; compatibility path with quoting and multiline drawbacks.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--project-path` is the normal choice when the CLI should prepare Unity for the project before execution.",
                "`--base-url` is for a direct service that is already known.",
                "`--unity-exe-path` is only valid with `--project-path`.",
                "Use exactly one script source: `--file`, `--stdin`, or `--code`.",
            ],
            "Timeout Rules": [
                "`--wait-timeout-ms` must be a positive integer.",
                "The command may return `running` when the wait budget ends before the job finishes.",
            ],
        },
        "status": {
            "success": [
                "`completed`: the script finished and any host return value is in `result`.",
                "`running`: the job is still running; use the returned `continuation_token` with `get-result`.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("not_available", direct_exec_client.EXIT_NOT_AVAILABLE, "the direct execution target could not be reached."),
                ("unity_start_failed", EXIT_UNITY_START_FAILED, "Unity could not be launched for the selected project."),
                ("unity_stalled", EXIT_UNITY_NOT_READY, "readiness stopped making progress before execution could proceed."),
                ("unity_not_ready", EXIT_UNITY_NOT_READY, "Unity did not become ready before execution could proceed."),
                ("failed", 1, "execution failed unexpectedly or the CLI rejected invalid execution input."),
            ],
        },
    },
    "get-result": {
        "quick_start": [
            "Continue waiting for an async execution job by using the `continuation_token` returned from `exec`.",
            "`unity-puer-exec get-result --continuation-token TOKEN`",
        ],
        "related_workflows": ("cold-start-exec-and-get-result",),
        "args": {
            "Arguments": [
                "`--continuation-token <token>`: required opaque token returned from a prior `exec` running result.",
                "`--wait-timeout-ms <ms>`: how long to wait before returning the current continuation state.",
            ],
            "Timeout Rules": [
                "`--wait-timeout-ms` must be a positive integer.",
                "The command may return another expected machine state instead of completing within one wait window.",
            ],
        },
        "status": {
            "success": [
                "`completed`: the async job finished and any host return value is in `result`.",
                "`running`: the job is still running; continue with the same `continuation_token`.",
            ],
            "failure": [
                ("compiling", direct_exec_client.EXIT_COMPILING, "the target is compiling and cannot satisfy the request yet."),
                ("not_available", direct_exec_client.EXIT_NOT_AVAILABLE, "the continuation target is not reachable right now."),
                ("missing", direct_exec_client.EXIT_MISSING, "the async job is no longer available on the continuation target."),
                ("session_missing", direct_exec_client.EXIT_SESSION_STATE, "the target no longer exposes the session continuity information needed for safe continuation."),
                ("session_stale", direct_exec_client.EXIT_SESSION_STATE, "the target session changed since the token was issued, so same-session continuation is unsafe."),
                ("failed", 1, "the token was malformed or another unexpected command failure occurred."),
            ],
        },
    },
    "ensure-stopped": {
        "quick_start": [
            "Check or enforce a stopped state for the selected target; this is not the normal graceful-exit workflow.",
            "`unity-puer-exec ensure-stopped --project-path X:/project --inspect-only`",
            "Normal exit workflows should prefer a script request such as `unity-puer-exec exec --project-path X:/project --file X:/exit.js`.",
        ],
        "related_workflows": (),
        "args": {
            "Arguments": [
                "`--project-path <path>`: inspect or stop a project-owned Unity process.",
                "`--base-url <url>`: inspect a direct service target without process control.",
                "`--timeout-seconds <seconds>`: wait budget for stop confirmation.",
                "`--inspect-only`: report whether the target is already stopped without changing it.",
                "`--immediate-kill`: skip graceful waiting and kill immediately; project mode only.",
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
    "cold-start-exec-and-get-result": {
        "goal": "Cold-start Unity for a project, run a file-based script, and continue a running job result with the returned continuation token.",
        "steps": [
            (
                "`unity-puer-exec exec --project-path X:/project --file X:/scripts/do-work.js --wait-timeout-ms 1000`",
                "Expected observation: the first response is a JSON object on stdout with `status = \"running\"` and a `continuation_token`.",
            ),
            (
                "`unity-puer-exec get-result --continuation-token TOKEN --wait-timeout-ms 1000`",
                "Expected observation: stdout stays machine-readable and eventually reaches `status = \"completed\"` when the job finishes.",
            ),
        ],
        "notice": [
            "`exec` is allowed to launch or recover Unity when you target a project with `--project-path`.",
            "`--file` is the preferred script input for multi-line or AI-generated scripts.",
            "`running` is an expected machine state, not an error; branch on it and continue with `get-result`.",
            "Treat `continuation_token` as opaque and reuse it rather than decoding or rebuilding it.",
        ],
    },
    "long-job-and-log-pattern": {
        "goal": "Observe a long-running workload without missing an early log milestone by registering log observation before starting the workload.",
        "steps": [
            (
                "`unity-puer-exec wait-for-log-pattern --project-path X:/project --pattern \"\\\\[FakeBuild\\\\] complete\" --timeout-seconds 0.1`",
                "Expected observation: the short initial wait may return a non-success wait state, but it establishes the observation point before the workload starts.",
            ),
            (
                "`unity-puer-exec exec --project-path X:/project --file X:/scripts/fake-build.js --wait-timeout-ms 200`",
                "Expected observation: the fake workload starts and may return `running` while Unity continues to print progress logs.",
            ),
            (
                "`unity-puer-exec wait-for-log-pattern --project-path X:/project --pattern \"\\\\[FakeBuild\\\\] complete\" --timeout-seconds 30`",
                "Expected observation: stdout eventually reports `status = \"completed\"` with `result.status = \"log_pattern_matched\"` once the milestone log appears.",
            ),
        ],
        "notice": [
            "This example uses a fake workload only to demonstrate the observation sequence; it is not a built-in compile command.",
            "Registering the first observation window before starting the workload reduces the chance of missing an early log line.",
            "`wait-for-log-pattern` matches from the current observation point rather than replaying the full historical Editor log.",
        ],
    },
    "request-editor-exit-via-exec": {
        "goal": "Request a normal Unity Editor exit through a script instead of using stopped-state control.",
        "steps": [
            {
                "command": "`unity-puer-exec exec --project-path X:/project --file X:/scripts/request-exit.js --wait-timeout-ms 1000`",
                "script_body": [
                    "const EditorApplication = puer.loadType('UnityEditor.EditorApplication');",
                    "EditorApplication.Exit(0);",
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
    sections = [
        "Overview\nunity-puer-exec is the primary CLI surface for preparing Unity, executing JavaScript, observing long-running work, and checking session state.",
        "Commands\n{}".format(_bullet_lines("{}: {}".format(name, TOP_LEVEL_COMMANDS[name]) for name in COMMANDS)),
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
