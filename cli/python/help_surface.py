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
            "wait-for-compile",
        ),
    ),
        (
            "Secondary / Troubleshooting",
            (
                "get-log-source",
                "get-log-briefs",
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
    "exec-and-wait-for-log-pattern",
    "recover-exec-by-request-id",
    "load-and-call-csharp-type",
    "derive-project-path-from-unity-api",
    "request-editor-exit-via-exec",
    "component-detection",
)


def _join_sections(sections):
    return "\n\n".join(section.rstrip() for section in sections if section).rstrip() + "\n"


def _bullet_lines(items):
    return "\n".join("- {}".format(item) for item in items)


TOP_LEVEL_COMMANDS = {
    "wait-for-log-pattern": "observe logs until a regular-expression pattern appears. See `wait-for-log-pattern --help`.",
    "wait-for-exec": "continue waiting on an accepted exec request by `request_id`. See `wait-for-exec --help`.",
    "wait-for-result-marker": "wait for the standard single-line JSON result marker emitted by a long-running script. See `wait-for-result-marker --help`.",
    "wait-for-compile": "edge-aware wait that brackets one Unity compile cycle (`compiling` appears, then returns to `ready`); use it after a refresh to defeat the async-compile race before reading compile errors. See `wait-for-compile --help`.",
    "get-log-source": "report the observable Unity log source for the selected target. See `get-log-source --help`.",
    "get-log-briefs": "return structured log brief entries for a byte range; use `log_range` from exec or wait-for-exec responses to specify the range. See `get-log-briefs --help`.",
    "get-blocker-state": "report whether a supported Unity modal blocker is currently detected for the target project. See `get-blocker-state --help`.",
    "resolve-blocker": "dismiss a supported Unity modal blocker for the target project with an explicit action. See `resolve-blocker --help`.",
    "exec": "run JavaScript against a project or direct service; primary entry for script execution. See `exec --help`.",
    "ensure-stopped": "check or force a stopped state; not the recommended graceful-exit path. See `ensure-stopped --help`.",
}

RECOMMENDED_PATH = (
    "For normal project-scoped work, start with `exec --project-path ...` (or omit `--project-path` when the exe is invoked from its installed location inside the Unity project).",
    "If `exec` returns `running`, continue with `wait-for-exec --request-id ...` or the script-specific observation path you designed.",
    "If an earlier step wrote C# or other import-triggering project assets, use the next project-scoped `exec --refresh-before-exec` instead of a separate readiness-only step.",
    "Use `wait-for-result-marker` after `exec` only when the script deliberately exposes a `correlation_id` workflow.",
    "If you need log-based verification, continue with `wait-for-log-pattern`.",
    "Use `get-blocker-state` when an exec-side timeout or stall might be caused by a supported Unity modal dialog.",
    "Use `resolve-blocker` only when you intentionally want the CLI to dismiss a supported modal blocker; then continue with the original `request_id` if needed.",
    "`get-log-source` and `ensure-stopped` are secondary commands, not the normal first step.",
)

TOP_LEVEL_WORKFLOWS = {
    "exec-and-wait-for-result-marker": "run a script that returns `correlation_id`, use `log_range.start` from the exec response, then wait for the terminal result marker.",
    "exec-and-wait-for-log-pattern": "run a script, use `log_range.start` from the exec response, then wait for the ordinary Unity log pattern that proves the intended result.",
    "recover-exec-by-request-id": "recover an accepted exec request by reusing or waiting on the same `request_id` after `running` or ambiguity.",
    "load-and-call-csharp-type": "learn the normal PuerTS-style bridge path for loading and calling Unity or C# types from JavaScript.",
    "derive-project-path-from-unity-api": "derive project-local paths through Unity APIs instead of assuming undocumented `ctx` fields.",
    "request-editor-exit-via-exec": "request a normal Unity Editor exit through `exec` instead of using `ensure-stopped`.",
    "component-detection": "use the standard PuerTS pattern for scene-inspection: puer.$typeof + puer.$ref + TryGetComponent + get_Item.",
}


COMMAND_HELP = {
    "wait-for-log-pattern": {
        "quick_start": [
            "Supporting observation command for log-based verification after or alongside `exec`.",
            "`unity-puer-exec wait-for-log-pattern --project-path X:/project --pattern \"\\\\[Build\\\\] done\"`",
            "Use this when task success is best verified through Unity log output; the pattern is a regular expression, not a literal string.",
        ],
        "related_workflows": ("exec-and-wait-for-log-pattern", "exec-and-wait-for-result-marker"),
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
    "wait-for-compile": {
        "quick_start": [
            "Supporting observation command that brackets a single Unity compilation cycle.",
            "`unity-puer-exec wait-for-compile --project-path X:/project`",
            "A refresh (`AssetDatabase.Refresh()` or `--refresh-before-exec`) starts compilation asynchronously, so polling `/health` immediately can read `ready` before `compiling` ever appears and `get-compile-errors` then returns the previous compilation's stale messages. This command is edge-aware: it first waits, within a bounded appear window, for `compiling` to appear (or detects a compile already in progress), then waits for the editor to return to `ready` -- so a just-issued recompile is observed instead of racing a stale `ready`.",
            "Trigger the recompile yourself, then call `wait-for-compile` before `get-compile-errors`; or use `exec --refresh-before-exec`, which performs the same refresh -> compile-settle -> execute lifecycle in one step.",
            "Trade-off: `AssetDatabase.Refresh()` only recompiles when it detects changed assets, so an unchanged project yields `no_compile_observed`. `CompilationPipeline.RequestScriptCompilation()` forces a recompile more deterministically; if a refresh reports `no_compile_observed` when you expected a rebuild, trigger compilation with `RequestScriptCompilation()` instead.",
        ],
        "related_workflows": (),
        "args": {
            "Arguments": [
                "`--project-path <path>`: resolve the project's control endpoint through the normal project-scoped discovery path.",
                "`--base-url <url>`: poll the supplied endpoint's `/health` directly, without project-identity validation or launch ownership.",
                "`--appear-timeout-seconds <seconds>`: bounded window to wait for `compiling` to appear after a refresh before concluding no compile was triggered; distinct from the settle timeout.",
                "`--settle-timeout-seconds <seconds>`: total budget for an observed compile to return to `ready`.",
                "`--health-timeout-seconds <seconds>`: timeout for each `/health` probe.",
                "`--include-diagnostics`: include top-level debug diagnostics (including the observed `/health` status sequence) in the machine-readable response.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--base-url` polls that endpoint directly; transient connection failures during a domain reload are tolerated as still-in-progress until the ready/timeout boundary.",
            ],
            "Timeout Rules": [
                "All timeout values must be positive numbers.",
                "The appear window bounds how long an unchanged project waits before returning `no_compile_observed`; keep it short.",
                "An observed compile that does not return to `ready` within the settle timeout yields a non-terminal `running` result, not a false completion.",
            ],
        },
        "status": {
            "success": [
                "`completed` with `result.status` `compile_settled` (`compile_observed` true): a compile cycle was observed and the editor is `ready` again.",
                "`completed` with `result.status` `no_compile_observed` (`compile_observed` false): no compilation appeared within the appear window and none was in progress; retry, or trigger compilation with `RequestScriptCompilation()` if you expected a rebuild.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("running", direct_exec_client.EXIT_RUNNING, "an observed compile did not return to ready within the settle timeout; re-run wait-for-compile to keep waiting."),
                ("unity_stalled", EXIT_UNITY_NOT_READY, "the project endpoint lost forward progress before a compile could be observed."),
                ("unity_not_ready", EXIT_UNITY_NOT_READY, "the project endpoint did not become ready while resolving the session."),
                ("failed", 1, "an unexpected wait-for-compile failure occurred."),
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
                "`--unity-log-path <path>`: explicit non-default Unity Editor log path for pre-session project-scoped discovery. Without it, a reachable project-owned Editor's own reported log path is preferred over the platform default.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Selector Rules": [
                "Use exactly one selector: `--project-path` or `--base-url`.",
                "`--project-path` is the normal choice when the CLI should discover the target from project context.",
                "`--base-url` is for a direct service that is already known.",
            ],
            "Range Rules": [
                "`result.resolution_tier` names which tier produced `result.path`, so a path the Editor stated is distinguishable from one the CLI assumed.",
                "`session_artifact`: an established session recorded this path; it outranks every other tier so observation keeps working when the control service is unreachable.",
                "`explicit_flag`: the caller supplied `--unity-log-path`.",
                "`control_service`: a reachable Editor owned by this project reported its own `console_log_path`. This is a stated path, not a guess.",
                "`platform_default`: nothing authoritative was available and the platform per-user `Editor.log` was assumed. Any other Unity Editor open on this machine writes to that same file, so byte offsets taken against it can be invalidated by an unrelated project.",
            ],
        },
        "status": {
            "success": [
                "`completed`: a log source is available and `result.status` is `log_source_available`.",
                "`result.resolution_tier` reports which resolution tier produced `result.path`.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("no_observation_target", EXIT_NO_OBSERVATION_TARGET, "no eligible Unity log source could be resolved for the selected target."),
                ("failed", 1, "an unexpected command failure occurred while resolving the observation target."),
            ],
        },
    },
    "get-log-briefs": {
        "quick_start": [
            "Secondary observation command for fetching structured log brief entries for a byte range.",
            "`unity-puer-exec get-log-briefs --project-path X:/project --range 12345-18920`",
            "Use the `log_range.start` and `log_range.end` values from an `exec` or `wait-for-exec` response to scope the range.",
            "Check `brief_sequence` in the exec response first; call `get-log-briefs` only when you need structured detail beyond what the sequence string provides.",
            "Brief grouping relies on Unity stack-trace logging being enabled (ScriptOnly/Full). When it is disabled (StackTraceLogType.None), log entries lose their delimiters and briefs are unreliable; this standalone command parses the raw range and cannot detect that, whereas exec / wait-for-exec report it via `stack_trace_logging.degraded` and a `!stacktrace-off` brief_sequence.",
            "To read one complete long entry instead of its 100-character preview, add `--full-text` together with `--include <index>`; combine with `--response-file` when the full text itself may be large.",
        ],
        "related_workflows": (),
        "args": {
            "Arguments": [
                "`--project-path <path>`: resolve the log source from a Unity project session artifact.",
                "`--unity-log-path <path>`: explicit Unity Editor log file path; takes priority over project session artifact.",
                "`--range START-END`: required byte range to parse; also accepts comma-separated `START,END` form.",
                "`--levels error,warning`: filter results to the specified comma-separated level names (`info`, `warning`, `error`, `unknown`).",
                "`--indexes 1,3,5`: select specific 1-based brief indices; union with `--levels` when both are supplied. `--include` is accepted as a backward-compatible alias with identical behavior.",
                "`--full-text`: attach the complete decoded text for each brief selected by `--indexes` (or its `--include` alias); requires explicit indices and does not change the default 100-character `text` preview.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
            ],
            "Range Rules": [
                "`--range` is required and must be two non-negative integers.",
                "Both `START-END` (hyphen) and `START,END` (comma) forms are accepted.",
                "Use `log_range.start` and `log_range.end` from an `exec` or `wait-for-exec` response as the source of truth for range values.",
            ],
            "Filter Rules": [
                "When neither `--levels` nor `--indexes` (or its `--include` alias) is supplied, all briefs in the range are returned.",
                "When both `--levels` and `--indexes` are supplied, the result is their union; no brief appears more than once.",
                "`--indexes` uses 1-based indices matching the `index` field in each brief entry; `--include` is a permanent backward-compatible alias for `--indexes` with identical behavior.",
                "If both `--indexes` and `--include` are supplied with different values, the CLI reports a usage error rather than silently preferring either flag.",
                "`--full-text` without `--indexes` (or its `--include` alias) is a usage error; full text is attached only to the explicitly selected indices, not to briefs pulled in only through `--levels`.",
            ],
        },
        "status": {
            "success": [
                "`completed`: `result` is a JSON array of brief objects, each with `index`, `level`, `line_count`, `start_offset`, `end_offset`, and `text` fields.",
                "With `--full-text --indexes ...` (or its `--include` alias): the selected briefs additionally carry `full_text` with the complete decoded entry text; unselected briefs and the default `text` preview are unchanged.",
            ],
            "failure": [
                ("full_text_requires_include", 2, "`--full-text` was supplied without `--indexes` (or its `--include` alias); pass one or more explicit 1-based brief indices."),
                ("conflicting_indexes_include", 2, "`--indexes` and `--include` were both supplied with different values."),
                ("failed", 1, "the range was invalid, the log file could not be read, an index-syntax value was not comma-separated integers, or another unexpected failure occurred."),
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
            "`unity-puer-exec exec --project-path X:/project --file X:/script.js --script-args '{\"mode\":\"dry-run\"}'`",
            "`unity-puer-exec exec --project-path X:/project --stdin < script.js`",
            "Every script source (`--file`, `--stdin`, `--code`) must use this module entry template: `export default function (ctx) { return null; }`",
            "The function's immediate return value is the machine-readable transport for structured data; it populates top-level `result`. For a result that may be large, add `--response-file X:/work/.tmp/result.json` to persist the complete response and receive a compact verifiable reference instead of routing large data through `console.log`, which remains a diagnostic/async-observation channel, not the preferred large-result transport.",
            "Script `ctx` is intentionally narrow: only `ctx.request_id`, `ctx.globals`, and `ctx.args` are guaranteed. See `exec --help-args` or `--help-example derive-project-path-from-unity-api` before assuming project-path helpers.",
            "With `--project-path`, `exec` owns Unity launch or recovery for the project as part of the main work lifecycle.",
            "Changed local modules are recovered by a same-invocation server-owned JsEnv reset by default; use `--stale-module-policy error` when `ctx.globals` or module singleton continuity must be preserved.",
            "Scripts use a PuerTS-style JavaScript-to-C# bridge; `puer.loadType(...)` is the normal way to load Unity or C# types inside `exec` scripts.",
            "If an earlier step wrote C# or other import-triggering project assets, make the next project-scoped `exec` use `--refresh-before-exec` and continue with `wait-for-exec` if the request stays non-terminal.",
        ],
        "related_workflows": (
            "recover-exec-by-request-id",
            "exec-and-wait-for-result-marker",
            "load-and-call-csharp-type",
            "derive-project-path-from-unity-api",
            "request-editor-exit-via-exec",
            "component-detection",
        ),
        "args": {
            "Arguments": [
                "`--project-path <path>`: select a Unity project and allow Unity launch when needed. Optional when the exe is invoked from its installed location inside the target Unity project.",
                "`--base-url <url>`: target an already-known direct service instead of a project.",
                "`--unity-exe-path <path>`: override the Unity executable for project-scoped startup only.",
                "`--unity-log-path <path>`: explicit Unity Editor log path for project-scoped startup, overriding the project-private log a CLI-launched Editor otherwise gets under the project's `Temp/`. An Editor the CLI did not launch keeps whatever log it was started with; the CLI discovers that path from the endpoint rather than assuming the platform default.",
                "`--wait-timeout-ms <ms>`: how long to wait before returning the current execution state.",
                "`--request-id <id>`: optional caller-owned exec identity for recovery or idempotent replay; omitted values are generated automatically.",
                "`--script-args <json-object>`: optional caller-supplied JSON object that becomes `ctx.args`; malformed JSON or non-object values fail before runtime execution.",
                "`--refresh-before-exec`: refresh the Unity project before running this script, settle on the resulting (asynchronously started) compile cycle, then run the script in the reloaded environment -- a single refresh -> compile-settle -> execute request lifecycle. Works in both `--project-path` and `--base-url` mode; in base-url mode the settle re-probes the same endpoint. The intermediate refreshing/compiling phase is non-terminal, and the terminal response carries the script result, not the `{refreshed: true}` refresh confirmation.",
                "`--reset-jsenv-before-exec`: ask the Unity server to perform one JsEnv reset immediately before this exec; the CLI does not issue a separate reset request.",
                "`--stale-module-policy auto-reset|error`: default `auto-reset` recovers changed or removed loaded local modules in the same invocation; `error` withholds reset and returns `module_cache_stale`, preserving JsEnv state. Automatic or explicit recovery reports affected module paths in `recovery`.",
                "`--include-diagnostics`: include top-level debug diagnostics in the machine-readable response.",
                "`--file <path>`: preferred script input for multi-line or AI-generated scripts; the file must export `default function (ctx) { ... }`.",
                "`--stdin`: read script content from standard input; stdin content must export `default function (ctx) { ... }`.",
                "`--code <inline-js>`: inline module-shaped source that still must export `default function (ctx) { ... }`; compatibility path with quoting and multiline drawbacks. PowerShell users: use single quotes (`'...'`) around `--code` values containing `$` (e.g., `$typeof`) to prevent variable expansion, or use `--file` instead.",
            ],
            "Selector Rules": [
                "Use at most one selector: `--project-path` or `--base-url`. Supplying both is a usage error.",
                "`--project-path` is the normal choice when the CLI should prepare Unity for the project before execution. When the exe is installed inside the target Unity project and invoked by its installed path, `--project-path` may be omitted; the CLI infers the project root from the exe location.",
                "`--refresh-before-exec` is valid with either selector and is intended for the next step after changing project assets or C# code. Because a refresh starts compilation asynchronously, the standalone `wait-for-compile` command is the supported way to bridge that race when you trigger the recompile separately.",
                "After a script writes C# or other import-triggering assets, prefer the next task `exec --refresh-before-exec` and stay on `wait-for-exec` for accepted continuation.",
                "`--base-url` is for a direct service that is already known.",
                "`--unity-exe-path` is only valid with `--project-path`.",
                "Use exactly one script source: `--file`, `--stdin`, or `--code`.",
                "Every script source must provide a full module entry, not a fragment: `export default function (ctx) { return null; }`.",
            ],
            "Bridge Model": [
                "`unity-puer-exec` scripts use a PuerTS-style JavaScript-to-C# bridge rather than ordinary JS imports for Unity/.NET APIs.",
                "`puer.loadType(...)` is the normal bridge entry for loading Unity or C# types inside the script.",
                "Bridged C# arrays and `List<T>` values are not plain JS arrays; prefer PuerTS-aware access patterns when collection behavior matters.",
                "Official JS-to-C# bridge reference: https://puerts.github.io/docs/puerts/unity/tutorial/js2cs",
            ],
            "Script Context": [
                "Guaranteed `ctx` fields are intentionally narrow: `ctx.request_id`, `ctx.globals`, and `ctx.args`.",
                "`ctx.request_id` matches the accepted top-level exec `request_id`.",
                "`ctx.globals` is mutable same-service shared state and is not described as durable across service restart or replacement.",
                "`ctx.args` is the caller-supplied JSON object from `--script-args`; when omitted, `ctx.args` is `{}`.",
                "Do not assume undocumented fields such as `ctx.project_path` are available unless the runtime contract is expanded explicitly.",
                "When a script needs project-local paths, derive them through supported Unity APIs such as `UnityEngine.Application.dataPath`, then use `System.IO.Path.GetDirectoryName(...)` to reach the project root.",
            ],
            "Timeout Rules": [
                "`--wait-timeout-ms` must be a positive integer.",
                "The command may return `running` when the wait budget ends before the request finishes.",
                "Reusing the same `--request-id` with equivalent execution content and equivalent canonical `--script-args` is recovery, not a duplicate execution attempt.",
                "The default-exported entry function must return an immediate JSON-serializable value; Promise return values complete with warning status (the function body still executes but the return value is not captured).",
            ],
        },
        "status": {
            "success": [
                "`completed`: the script finished; the accepted response includes `request_id`, `log_range`, `brief_sequence`, and the default-exported entry function's immediate return value is in `result`.",
                "`running`: the request is still active; continue with `wait-for-exec --request-id ...` or the script's own observation workflow. The response always includes `log_range` and `brief_sequence` for the observation window so far.",
                "When `phase` is present, it names the current request stage without changing the top-level `running` contract; first-version values may include `refreshing`, `compiling`, and `executing`.",
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
                ("failed", 1, "execution failed unexpectedly, the module entry shape was invalid, or another non-warning execution error occurred."),
                ("warning", 0, "the script body executed successfully but the entry function returned a Promise; the return value could not be serialized. Use console.log() with wait-for-result-marker for async result observation."),
                ("module_cache_stale", direct_exec_client.EXIT_MODULE_CACHE_STALE, "one or more loaded local modules changed or were removed; `--stale-module-policy error` withheld reset so JsEnv state is preserved. Choose explicit reset or omit the error policy for same-invocation auto recovery."),
                ("unity_compile_error", direct_exec_client.EXIT_UNITY_COMPILE_ERROR, "C# compilation has errors; the script was not executed. Fix the C# errors and re-run with --refresh-before-exec to trigger recompilation."),
            ],
        },
    },
    "wait-for-exec": {
        "quick_start": [
            "Preferred follow-up when you already know an accepted exec `request_id` and want to continue waiting without resubmitting script content.",
            "`unity-puer-exec wait-for-exec --project-path X:/project --request-id RID`",
            "Use this after `exec` returns `running`, or after an ambiguous timeout when you intentionally want recovery with the same `request_id`.",
            "If an earlier `exec` result was too large to fully inspect inline, `wait-for-exec --request-id RID --response-file X:/work/.tmp/recovered.json` recovers the retained completed response by the same `request_id` without re-running the script.",
        ],
        "related_workflows": ("recover-exec-by-request-id",),
        "args": {
            "Arguments": [
                "`--project-path <path>`: select a Unity project and allow Unity launch when needed. Optional when the exe is invoked from its installed location inside the target Unity project.",
                "`--base-url <url>`: target an already-known direct service instead of a project.",
                "`--unity-exe-path <path>`: override the Unity executable for project-scoped startup only.",
                "`--unity-log-path <path>`: explicit Unity Editor log path for project-scoped startup, overriding the project-private log a CLI-launched Editor otherwise gets under the project's `Temp/`. An Editor the CLI did not launch keeps whatever log it was started with; the CLI discovers that path from the endpoint rather than assuming the platform default.",
                "`--request-id <id>`: required accepted exec identity to continue waiting on.",
                "`--wait-timeout-ms <ms>`: how long to wait before returning the current request state again.",
                "`--log-start-offset <offset>`: optional log observation start offset; pass `log_range.start` from the original `exec` response so `brief_sequence` remains consistent with the cumulative observed log activity across successive calls.",
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
                "`missing` means the addressed service currently has no recoverable record for that `request_id`, including local pending artifacts that have already expired or were cleaned up as malformed leftovers.",
            ],
        },
        "status": {
            "success": [
                "`completed`: the request finished and any immediate entry return value is in `result`.",
                "`running`: the request is still active and can be waited on again with the same `request_id`.",
                "When `phase` is present, treat it as diagnostic detail for the current stage, not as a different follow-up command family.",
            ],
            "failure": [
                ("address_conflict", 2, "both selectors were provided; choose exactly one."),
                ("modal_blocked", direct_exec_client.EXIT_MODAL_BLOCKED, "a supported Unity modal dialog is blocking the accepted exec request; inspect `blocker.type` and avoid starting a fresh request."),
                ("missing", direct_exec_client.EXIT_MISSING, "the addressed service has no recoverable record for that `request_id`, including expired or malformed local pending leftovers."),
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
            "Use the `correlation_id` from the script workflow and the `log_range.start` returned by `exec` or `wait-for-exec`.",
        ],
        "related_workflows": ("exec-and-wait-for-result-marker",),
        "args": {
            "Arguments": [
                "`--project-path <path>` or `--base-url <url>`: select the observation target.",
                "`--unity-log-path <path>`: explicit non-default Unity Editor log path for pre-session project-scoped observation.",
                "`--correlation-id <id>`: required result-marker correlation id to match.",
                "`--start-offset <offset>`: optional starting log offset; use `log_range.start` from the `exec` or `wait-for-exec` response as the observation checkpoint.",
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
        "goal": "Run a long-running script and wait for the terminal result marker once the script has made the intended `correlation_id` available; use `log_range.start` from the exec response as the observation checkpoint.",
        "steps": [
            {
                "command": "`unity-puer-exec exec --project-path X:/project --file X:/scripts/do-work.js --wait-timeout-ms 1000`",
                "script_body": [
                    "export default function run(ctx) {",
                    "  const correlation_id = ctx.request_id;",
                    "  console.log('[UnityPuerExecResult] ' + JSON.stringify({ correlation_id, status: 'started' }));",
                    "  return { correlation_id };",
                    "}",
                ],
                "observation": "Expected observation: stdout returns machine-readable JSON with `request_id` and `log_range`. If the script finishes within the wait budget, the immediate entry return value is in `result`. If the script is still active, the response uses `status = \"running\"`. Read `log_range.start` from the response to use as the observation checkpoint.",
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
            "Use `log_range.start` plus the script-provided `correlation_id` together so observation begins after the originating `exec` request.",
            "If the session has not yet produced `session_marker` and you intentionally use a non-default Unity log file, keep passing the same `--unity-log-path` on the log-related commands in that workflow.",
        ],
    },
    "exec-and-wait-for-log-pattern": {
        "goal": "Run a script and verify success through ordinary Unity log output without falling back to direct host-log inspection; use `log_range.start` from the exec response as the observation checkpoint.",
        "steps": [
            {
                "command": "`unity-puer-exec exec --project-path X:/project --file X:/scripts/emit-build-log.js --wait-timeout-ms 1000`",
                "script_body": [
                    "export default function run(ctx) {",
                    "  console.log('[Build] done for request ' + ctx.request_id);",
                    "  return { request_id: ctx.request_id, status: 'emitted-log-line' };",
                    "}",
                ],
                "observation": "Expected observation: stdout returns machine-readable JSON with the immediate `result` and `log_range`. Read `log_range.start` from the response so later observation can start from the same checkpoint.",
            },
            (
                "`unity-puer-exec wait-for-log-pattern --project-path X:/project --start-offset OFFSET --pattern \"\\\\[Build\\\\] done for request REQ\"`",
                "Expected observation: stdout stays machine-readable and eventually reaches `status = \"completed\"` with `result.status = \"log_pattern_matched\"`.",
            ),
        ],
        "notice": [
            "Use this workflow when success is confirmed by ordinary Unity log output rather than by a correlation-aware result marker.",
            "Read `log_range.start` from the `exec` response and pass it to `wait-for-log-pattern --start-offset` so observation begins after the originating request.",
            "If the first observation window was missed, prefer creating a fresh safe checkpoint through a new exec-side attempt rather than falling back to direct host-log inspection.",
            "The pattern is a regular expression; escape special characters such as `[` and `]` when you need a literal match.",
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
            "Reusing the same `request_id` with equivalent execution content and equivalent canonical `--script-args` is recovery. Using a fresh `request_id` starts a new execution attempt.",
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
    "load-and-call-csharp-type": {
        "goal": "Use the normal PuerTS-style bridge path to load Unity or C# types from JavaScript before building a larger task-specific script.",
        "steps": [
            {
                "command": "`unity-puer-exec exec --project-path X:/project --file X:/scripts/bridge-probe.js --script-args '{\"a\":7,\"b\":5}' --wait-timeout-ms 1000`",
                "script_body": [
                    "export default function run(ctx) {",
                    "  const Math = puer.loadType('System.Math');",
                    "  const EditorApplication = puer.loadType('UnityEditor.EditorApplication');",
                    "  return {",
                    "    request_id: ctx.request_id,",
                    "    maxValue: Math.Max(ctx.args.a, ctx.args.b),",
                    "    args: ctx.args,",
                    "    isCompiling: EditorApplication.isCompiling,",
                    "  };",
                    "}",
                ],
                "observation": "Expected observation: stdout returns machine-readable JSON with the immediate `result`; `ctx.args` echoes the caller input, `maxValue` confirms those arguments reached the script, and `isCompiling` shows a bridged Unity Editor property read.",
            },
        ],
        "notice": [
            "This is the intended bridge model for Unity and .NET access inside `exec` scripts: use `puer.loadType(...)` to load types before calling members.",
            "If a script in this bridge workflow writes C# or other import-triggering assets, run the next project-scoped `exec` with `--refresh-before-exec` so compile recovery stays attached to that request.",
            "Treat bridged C# arrays and `List<T>` values as bridged .NET objects, not plain JS arrays with identical semantics.",
            "For deeper bridge rules such as generics, `CS.*`, or collection behavior, consult the official JS-to-C# reference: https://puerts.github.io/docs/puerts/unity/tutorial/js2cs",
        ],
    },
    "component-detection": {
        "goal": "Use the standard PuerTS pattern for scene-inspection scripts: direct `CS.UnityEngine.X` access for static members and instance calls, `puer.$typeof(CS.UnityEngine.X)` only where a `System.Type` value is required as a parameter (such as the `TryGetComponent` type argument), `puer.$ref()` for out-parameter references, `TryGetComponent` for component probing, and `get_Item()` for C# indexer access on bridged collections.",
        "steps": [
            {
                "command": "`unity-puer-exec exec --project-path X:/project --file X:/scripts/inspect-scene.js --script-args '{\"scenePath\":\"Assets/Scenes/Main.unity\"}' --wait-timeout-ms 1000`",
                "script_body": [
                    "export default function run(ctx) {",
                    "  const scene = CS.UnityEngine.SceneManagement.SceneManager.GetActiveScene();",
                    "  const rootGOs = scene.GetRootGameObjects();",
                    "",
                    "  const results = [];",
                    "  for (let i = 0; i < rootGOs.Length; i++) {",
                    "    const go = rootGOs.get_Item(i);",
                    "    const mf = puer.$ref();",
                    "    const hasMF = go.TryGetComponent(",
                    "      puer.$typeof(CS.UnityEngine.MeshFilter), mf",
                    "    );",
                    "    results.push({",
                    "      name: go.name,",
                    "      hasMeshFilter: hasMF,",
                    "      meshName: hasMF ? mf.value.sharedMesh.name : null,",
                    "    });",
                    "  }",
                    "  return { request_id: ctx.request_id, rootCount: results.length, results };",
                    "}",
                ],
                "observation": "Expected observation: stdout returns machine-readable JSON with the immediate `result`; `results` is a JS array of per-GameObject inspection data using the standard component-detection pattern.",
            },
        ],
        "notice": [
            "Use direct `CS.UnityEngine.X` access for ordinary static and instance member access (as with `CS.UnityEngine.SceneManagement.SceneManager.GetActiveScene()`); only wrap a type in `puer.$typeof(CS.UnityEngine.X)` when a `System.Type` value is required as a parameter, such as the type argument to `TryGetComponent`.",
            "Generic instance methods like `go.GetComponents(MeshFilter)` are not supported by PuerTS; use the non-generic `TryGetComponent(type, puer.$ref())` instead.",
            "C# indexers must be called as `get_Item(i)` in PuerTS; the JS bracket syntax `roots[i]` does not work on bridged .NET collections.",
            "`puer.$ref()` creates an out-parameter placeholder; after calling `TryGetComponent`, read the resolved value via `.value` on the ref object.",
            "For runtime type introspection, note that `comp.GetType().Name` is not available in the PuerTS bridge; use explicit type-by-type probing with `TryGetComponent` as shown.",
            "`scene.GetRootGameObjects()` returns a bridged C# array, not a plain JS array; use `.Length` and `get_Item(i)` for enumeration.",
        ],
    },
    "derive-project-path-from-unity-api": {
        "goal": "Derive project-local paths through supported Unity APIs instead of assuming undocumented script-context fields.",
        "steps": [
            {
                "command": "`unity-puer-exec exec --project-path X:/project --file X:/scripts/write-validation-asset.js --wait-timeout-ms 1000`",
                "script_body": [
                    "export default function run(ctx) {",
                    "  const Application = puer.loadType('UnityEngine.Application');",
                    "  const Path = puer.loadType('System.IO.Path');",
                    "  const projectRoot = Path.GetDirectoryName(Application.dataPath);",
                    "  return { request_id: ctx.request_id, projectRoot, assetsPath: Application.dataPath };",
                    "}",
                ],
                "observation": "Expected observation: stdout returns machine-readable JSON with the immediate `result`; `projectRoot` is derived from `Application.dataPath` rather than from an assumed `ctx.project_path` field.",
            },
        ],
        "notice": [
            "The public `ctx` contract is intentionally narrow: rely on `ctx.request_id`, `ctx.globals`, and `ctx.args`, not undocumented fields.",
            "`Application.dataPath` points at the project's `Assets` directory; `System.IO.Path.GetDirectoryName(...)` gives the project root when needed.",
            "Use normal Unity or .NET APIs for file IO after deriving the path you need.",
        ],
    },
}


_OPTIONAL_FORWARDED_ARGS = {
    "wait-for-exec": (
        ("--wait-timeout-ms", "wait_timeout_ms"),
        ("--unity-exe-path", "unity_exe_path"),
        ("--unity-log-path", "unity_log_path"),
    ),
    "exec": (
        ("--unity-exe-path", "unity_exe_path"),
        ("--unity-log-path", "unity_log_path"),
    ),
    "wait-for-log-pattern": (
        ("--unity-log-path", "unity_log_path"),
    ),
    "wait-for-result-marker": (
        ("--unity-log-path", "unity_log_path"),
    ),
    "get-log-source": (
        ("--unity-log-path", "unity_log_path"),
    ),
    "get-log-briefs": (
        ("--unity-log-path", "unity_log_path"),
    ),
}

GUIDANCE_MATRIX = {
    # --- exec ---
    ("exec", "running"): {
        "next_steps": [
            {
                "command": "wait-for-exec",
                "when": "you want to continue waiting for the accepted request to finish",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
            {
                "command": "wait-for-result-marker",
                "when": "the script deliberately exposes a correlation_id and you want to wait for the terminal result marker",
            },
            {
                "command": "wait-for-log-pattern",
                "when": "you want to verify success through ordinary Unity log output rather than a result marker",
            },
        ],
    },
    ("exec", "completed"): {},
    ("exec", "modal_blocked"): {
        "situation": "A supported Unity modal dialog is blocking exec progress. Inspect the blocker type before deciding whether to resolve it.",
        "next_steps": [
            {
                "command": "get-blocker-state",
                "when": "you want to confirm the specific blocker type before acting",
                "argv_template": [
                    "unity-puer-exec", "get-blocker-state",
                    "--project-path", "{project_path}",
                ],
            },
            {
                "command": "resolve-blocker",
                "when": "you have confirmed a supported modal blocker and machine-issued cancel is acceptable",
                "argv_template": [
                    "unity-puer-exec", "resolve-blocker",
                    "--project-path", "{project_path}",
                    "--action", "cancel",
                ],
            },
            {
                "command": "wait-for-exec",
                "when": "the blocker has been resolved and you want to continue waiting on the same request",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
        ],
    },
    ("exec", "busy"): {
        "situation": "A different exec request is already active on this service. Wait for the current request to finish or use wait-for-exec with its request_id.",
    },
    ("exec", "not_available"): {
        "situation": "The execution target could not be reached. Project-scoped exec already attempted Unity launch/recovery before returning this status.",
    },
    ("exec", "request_id_conflict"): {
        "situation": "The provided request_id is already associated with different execution content. Use a fresh request_id for a new execution attempt, or resubmit with the original content for recovery.",
    },
    ("exec", "launch_conflict"): {
        "situation": "Project-scoped launch ownership could not be established safely. Another process may be launching Unity for this project.",
    },
    ("exec", "unity_start_failed"): {
        "situation": "Unity could not be launched for the selected project.",
        "next_steps": [
            {
                "command": "wait-for-exec",
                "when": "a pending exec artifact exists and Unity may become available after the launch issue is resolved",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
        ],
    },
    ("exec", "unity_stalled"): {
        "situation": "Readiness stopped making progress before execution could proceed.",
        "next_steps": [
            {
                "command": "get-blocker-state",
                "when": "the stall might be caused by a supported Unity modal dialog",
                "argv_template": [
                    "unity-puer-exec", "get-blocker-state",
                    "--project-path", "{project_path}",
                ],
            },
            {
                "command": "wait-for-exec",
                "when": "a pending exec artifact exists and Unity may resume progress",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
        ],
    },
    ("exec", "unity_not_ready"): {
        "situation": "Unity did not become ready before the readiness budget expired.",
        "next_steps": [
            {
                "command": "wait-for-exec",
                "when": "a pending exec artifact exists and you want to retry after more time",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
        ],
    },
    ("exec", "failed"): {
        "situation": "An unexpected execution failure occurred. Check the error field for details. Note: if the error is async_result_not_supported, the script body executed but returned a Promise - use exec --help-status to see the warning status.",
    },
    ("exec", "warning"): {
        "situation": "The script body executed successfully, but the entry function returned a Promise (async_result_not_supported). Any synchronous side effects have already taken effect. Use console.log() with wait-for-result-marker for async result observation.",
        "next_steps": [
            {
                "command": "wait-for-result-marker",
                "when": "the script uses a correlation_id and you want to observe the terminal result marker",
            },
        ],
    },
    ("exec", "module_cache_stale"): {
        "situation": "One or more local modules loaded by the current JsEnv changed or were removed. Reset was withheld because `--stale-module-policy error` was selected, so the script was not executed and existing JsEnv state was preserved.",
        "next_steps": [
            {
                "command": "exec",
                "when": "re-run with --reset-jsenv-before-exec to clear the module cache and execute the updated file",
                "argv_template": [
                    "unity-puer-exec", "exec",
                    "--project-path", "{project_path}",
                    "--file", "{file_path}",
                    "--reset-jsenv-before-exec",
                ],
            },
            {
                "command": "exec",
                "when": "use the default same-invocation recovery when preserving JsEnv state is not required",
                "argv_template": [
                    "unity-puer-exec", "exec",
                    "--project-path", "{project_path}",
                    "--file", "{file_path}",
                    "--stale-module-policy", "auto-reset",
                ],
            },
        ],
    },
    ("exec", "unity_compile_error"): {
        "situation": "C# compilation has errors that must be fixed before executing scripts. The script was not executed. Check compile_errors_total and compile_messages in this response for immediate context, or use get-compile-errors for the full list.",
        "next_steps": [
            {
                "command": "exec",
                "when": "after fixing the C# errors, re-run with --refresh-before-exec to trigger recompilation",
                "argv_template": [
                    "unity-puer-exec", "exec",
                    "--project-path", "{project_path}",
                    "--file", "{file_path}",
                    "--refresh-before-exec",
                ],
            },
            {
                "command": "get-compile-errors",
                "when": "you need the full list of compile errors to understand what needs fixing",
                "argv_template": [
                    "unity-puer-exec", "get-compile-errors",
                    "--project-path", "{project_path}",
                ],
            },
            {
                "command": "get-compile-warnings",
                "when": "you want to inspect compile warnings separately",
                "argv_template": [
                    "unity-puer-exec", "get-compile-warnings",
                    "--project-path", "{project_path}",
                ],
            },
        ],
    },
    # --- wait-for-exec ---
    ("wait-for-exec", "running"): {
        "next_steps": [
            {
                "command": "wait-for-exec",
                "when": "you want to continue waiting for the same request",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
            {
                "command": "wait-for-result-marker",
                "when": "the script exposes a correlation_id and you want to observe the terminal result marker instead",
            },
            {
                "command": "wait-for-log-pattern",
                "when": "you want to verify progress or success through ordinary Unity log output",
            },
        ],
    },
    ("wait-for-exec", "completed"): {},
    ("wait-for-exec", "modal_blocked"): {
        "situation": "A supported Unity modal dialog is blocking the accepted exec request. Do not start a fresh request; resolve the blocker first.",
        "next_steps": [
            {
                "command": "get-blocker-state",
                "when": "you want to confirm the specific blocker type before acting",
                "argv_template": [
                    "unity-puer-exec", "get-blocker-state",
                    "--project-path", "{project_path}",
                ],
            },
            {
                "command": "resolve-blocker",
                "when": "you have confirmed a supported modal blocker and machine-issued cancel is acceptable",
                "argv_template": [
                    "unity-puer-exec", "resolve-blocker",
                    "--project-path", "{project_path}",
                    "--action", "cancel",
                ],
            },
            {
                "command": "wait-for-exec",
                "when": "the blocker has been resolved and you want to continue the same request",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
        ],
    },
    ("wait-for-exec", "missing"): {
        "situation": "The addressed service has no recoverable record for that request_id. The request may have completed, expired, or never been submitted.",
        "next_steps": [
            {
                "command": "exec",
                "when": "you need to resubmit the script as a new execution attempt",
            },
        ],
    },
    ("wait-for-exec", "not_available"): {
        "situation": "The execution target could not be reached.",
    },
    ("wait-for-exec", "launch_conflict"): {
        "situation": "Project-scoped launch ownership could not be established safely. Another process may be launching Unity for this project.",
    },
    ("wait-for-exec", "unity_start_failed"): {
        "situation": "Unity could not be launched for the selected project.",
        "next_steps": [
            {
                "command": "wait-for-exec",
                "when": "Unity may become available after the launch issue is resolved",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
        ],
    },
    ("wait-for-exec", "unity_stalled"): {
        "situation": "Readiness stopped making progress before waiting could proceed.",
        "next_steps": [
            {
                "command": "get-blocker-state",
                "when": "the stall might be caused by a supported Unity modal dialog",
                "argv_template": [
                    "unity-puer-exec", "get-blocker-state",
                    "--project-path", "{project_path}",
                ],
            },
            {
                "command": "wait-for-exec",
                "when": "Unity may resume progress and you want to keep waiting",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
        ],
    },
    ("wait-for-exec", "unity_not_ready"): {
        "situation": "Unity did not become ready before waiting could proceed.",
        "next_steps": [
            {
                "command": "wait-for-exec",
                "when": "you want to retry after more time",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
        ],
    },
    ("wait-for-exec", "unity_compile_error"): {
        "situation": "C# compilation has errors that must be fixed before the pending exec request can proceed. The script has not been executed.",
        "next_steps": [
            {
                "command": "exec",
                "when": "after fixing the C# errors, re-run exec with --refresh-before-exec to trigger recompilation",
                "argv_template": [
                    "unity-puer-exec", "exec",
                    "--project-path", "{project_path}",
                    "--file", "{file_path}",
                    "--refresh-before-exec",
                ],
            },
            {
                "command": "get-compile-errors",
                "when": "you need the full list of compile errors to understand what needs fixing",
                "argv_template": [
                    "unity-puer-exec", "get-compile-errors",
                    "--project-path", "{project_path}",
                ],
            },
        ],
    },
    ("wait-for-exec", "failed"): {
        "situation": "An unexpected wait-for-exec failure occurred. Check the error field for details.",
    },
    # --- wait-for-log-pattern ---
    ("wait-for-log-pattern", "completed"): {},
    ("wait-for-log-pattern", "no_observation_target"): {
        "situation": "No eligible Unity log source could be observed for the selected target.",
        "next_steps": [
            {
                "command": "get-log-source",
                "when": "you need to diagnose whether a log source exists for this target",
                "argv_template": [
                    "unity-puer-exec", "get-log-source",
                    "--project-path", "{project_path}",
                ],
            },
        ],
    },
    ("wait-for-log-pattern", "unity_stalled"): {
        "situation": "Observation lost forward progress before the pattern appeared.",
        "next_steps": [
            {
                "command": "get-blocker-state",
                "when": "the stall might be caused by a supported Unity modal dialog",
                "argv_template": [
                    "unity-puer-exec", "get-blocker-state",
                    "--project-path", "{project_path}",
                ],
            },
        ],
    },
    ("wait-for-log-pattern", "unity_not_ready"): {
        "situation": "The observed target stopped being ready while waiting for the pattern.",
    },
    ("wait-for-log-pattern", "failed"): {
        "situation": "The pattern observation failed unexpectedly. Check the error field for details.",
    },
    # --- wait-for-result-marker ---
    ("wait-for-result-marker", "completed"): {},
    ("wait-for-result-marker", "no_observation_target"): {
        "situation": "No eligible Unity log source could be observed for the selected target.",
        "next_steps": [
            {
                "command": "get-log-source",
                "when": "you need to diagnose whether a log source exists for this target",
                "argv_template": [
                    "unity-puer-exec", "get-log-source",
                    "--project-path", "{project_path}",
                ],
            },
        ],
    },
    ("wait-for-result-marker", "session_missing"): {
        "situation": "The target no longer exposes the session continuity information needed for safe guarded observation.",
    },
    ("wait-for-result-marker", "session_stale"): {
        "situation": "The target session changed since the expected session marker was recorded. Observation results may not correspond to the original execution.",
    },
    ("wait-for-result-marker", "unity_stalled"): {
        "situation": "Observation lost forward progress before the result marker appeared.",
        "next_steps": [
            {
                "command": "get-blocker-state",
                "when": "the stall might be caused by a supported Unity modal dialog",
                "argv_template": [
                    "unity-puer-exec", "get-blocker-state",
                    "--project-path", "{project_path}",
                ],
            },
        ],
    },
    ("wait-for-result-marker", "unity_not_ready"): {
        "situation": "The observed target stopped being ready while waiting for the result marker.",
    },
    ("wait-for-result-marker", "failed"): {
        "situation": "The result marker observation failed unexpectedly. Check the error field for details.",
    },
    # --- ensure-stopped ---
    ("ensure-stopped", "completed"): {},
    ("ensure-stopped", "not_stopped"): {
        "situation": "The target is still not stopped under the selected stop mode.",
        "next_steps": [
            {
                "command": "ensure-stopped",
                "when": "you want to force-stop with --immediate-kill",
            },
        ],
    },
    ("ensure-stopped", "failed"): {
        "situation": "An unexpected failure occurred while checking or enforcing the stopped state.",
    },
    # --- get-blocker-state ---
    ("get-blocker-state", "completed"): {
        "next_steps": [
            {
                "command": "resolve-blocker",
                "when": "result.status is modal_blocked and you want to dismiss the blocker",
                "argv_template": [
                    "unity-puer-exec", "resolve-blocker",
                    "--project-path", "{project_path}",
                    "--action", "cancel",
                ],
            },
        ],
    },
    ("get-blocker-state", "failed"): {
        "situation": "An unexpected blocker-query failure occurred.",
    },
    # --- resolve-blocker ---
    ("resolve-blocker", "completed"): {
        "next_steps": [
            {
                "command": "wait-for-exec",
                "when": "you had a pending exec request and want to continue it after resolving the blocker",
                "argv_template": [
                    "unity-puer-exec", "wait-for-exec",
                    "--project-path", "{project_path}",
                    "--request-id", "{request_id}",
                ],
            },
            {
                "command": "exec",
                "when": "you want to start a new execution attempt after resolving the blocker",
            },
        ],
    },
    ("resolve-blocker", "no_supported_blocker"): {
        "situation": "No supported blocker was currently detected. The dialog may have already been dismissed or is not a supported blocker type.",
    },
    ("resolve-blocker", "resolution_failed"): {
        "situation": "A supported blocker was detected but the cancel interaction could not be completed safely or confirmed.",
    },
    ("resolve-blocker", "unsupported_operation"): {
        "situation": "Blocker resolution requires Windows and --project-path in the first version.",
    },
    ("resolve-blocker", "failed"): {
        "situation": "An unexpected resolution failure occurred.",
    },
    # --- get-log-briefs ---
    ("get-log-briefs", "completed"): {
        "next_steps": [
            {
                "command": "get-log-source",
                "when": "you need the full log file path for deeper inspection beyond brief entries",
            },
        ],
    },
    ("get-log-briefs", "failed"): {
        "situation": "The brief retrieval failed. The range may be invalid or the log file could not be read.",
    },
    # --- get-log-source: no guidance (task 1.7) ---
    # --- wait-for-compile ---
    ("wait-for-compile", "running"): {
        "situation": "An observed compile has not returned to ready within the settle timeout. This is a non-terminal compiling phase, not a completed compile cycle; do not read compile errors yet.",
        "next_steps": [
            {
                "command": "wait-for-compile",
                "when": "you want to keep waiting for the same compile cycle to settle",
                "argv_template": [
                    "unity-puer-exec", "wait-for-compile",
                    "--project-path", "{project_path}",
                ],
            },
            {
                "command": "get-compile-errors",
                "when": "the compile has settled to ready and you want to read the fresh results",
                "argv_template": [
                    "unity-puer-exec", "get-compile-errors",
                    "--project-path", "{project_path}",
                ],
            },
        ],
    },
    ("wait-for-compile", "no_compile_observed"): {
        "situation": "No compilation appeared within the appear window and none was in progress. If a refresh ran but no assets changed, AssetDatabase.Refresh() triggers no compile; trigger CompilationPipeline.RequestScriptCompilation() if you expected a rebuild, otherwise proceed.",
        "next_steps": [
            {
                "command": "get-compile-errors",
                "when": "you are confident the previous compile results are current and want to read them",
                "argv_template": [
                    "unity-puer-exec", "get-compile-errors",
                    "--project-path", "{project_path}",
                ],
            },
        ],
    },
}


# The matrix key is (command, status) and carries no guard identity, so the
# per-guard wording lives here and overrides the entry's default `situation`.
VERSION_MISMATCH_SITUATIONS = {
    "bridge": (
        "The CLI executable and the Unity Editor package ship as one release, so the two "
        "observed versions indicate a mixed installation. The Unity bridge is running a "
        "different release than the CLI that contacted it."
    ),
    "package_layout": (
        "The executable does not match the package tree it is installed in: its own version "
        "differs from the `version` declared by the adjacent `package.json`, so the binary is "
        "left over from a different release than the Editor scripts beside it."
    ),
    "bridge_version_unknown": (
        "The Unity bridge reported no version. It predates version reporting and therefore "
        "cannot be verified as compatible with this CLI."
    ),
    "cli_version_unknown": (
        "This executable carries no stamped version. It predates version reporting, or was "
        "built without the stamping step, and therefore cannot be verified as compatible with "
        "the Unity Editor package it is installed with."
    ),
}

_VERSION_MISMATCH_GUIDANCE = {
    "situation": (
        "The CLI executable and the Unity Editor package ship as one release, so the two "
        "observed versions indicate a mixed installation. Reconcile the installation so both "
        "halves come from the same release."
    ),
    "next_steps": [
        {
            "command": "--version",
            "when": "you want to confirm which CLI build is acting before reconciling the installation",
            "argv": ["unity-puer-exec", "--version"],
        },
    ],
}

# Both local guards run before any command work, so every command can refuse on a
# version mismatch -- not only the ones that contact the control service.
for _version_guard_command in COMMANDS:
    GUIDANCE_MATRIX[(_version_guard_command, "version_mismatch")] = _VERSION_MISMATCH_GUIDANCE

VERSION_MISMATCH_STATUS_LINE = (
    "`version_mismatch` -> exit {}: the CLI executable and the Unity Editor package are from "
    "different releases, or one half cannot state its version. The command performs no work; "
    "reconcile the installation so both halves come from the same release. There is no bypass."
).format(direct_exec_client.EXIT_VERSION_MISMATCH)


# Commands that accept a caller-supplied log start offset, and can therefore report
# that the offset stopped denoting the content the caller meant.
LOG_OFFSET_AWARE_COMMANDS = ("wait-for-exec", "wait-for-log-pattern", "wait-for-result-marker")

LOG_OFFSETS_INVALIDATED_HELP_LINES = (
    "`log_offsets_invalidated` is an additive response field, not a status: the exit code and "
    "the rest of the response are unchanged, and the command still returns whatever the observed "
    "log currently contains rather than refusing to read.",
    "It appears when the supplied start offset is past the end of the observed log. The log was "
    "rotated or truncated, so byte offsets recorded before that no longer denote the content they "
    "did; the scan restarted from the beginning of the file.",
    "The field names the observed log path, the supplied start, and the observed end. Discard the "
    "stale `log_range` and re-observe without an offset instead of reusing it.",
    "If the named path is the platform default per-user `Editor.log`, a second Unity Editor is "
    "very likely sharing that file and invalidating the offsets. Run `get-log-source` and check "
    "`resolution_tier`: `control_service` or `session_artifact` means the observed log belongs to "
    "the target Editor, while `platform_default` means the path was assumed, not stated.",
)


def _build_argv(template, target_command, context):
    if not context:
        return None
    argv = []
    for item in template:
        if item.startswith("{") and item.endswith("}"):
            key = item[1:-1]
            value = context.get(key)
            if value is None:
                return None
            argv.append(str(value))
        else:
            argv.append(item)
    forwarded = _OPTIONAL_FORWARDED_ARGS.get(target_command, ())
    for flag, key in forwarded:
        value = context.get(key)
        if value:
            argv.extend([flag, str(value)])
    if context.get("include_diagnostics"):
        argv.append("--include-diagnostics")
    return argv


def build_next_steps(command, status, context):
    entry = GUIDANCE_MATRIX.get((command, status))
    if entry is None:
        return None
    templates = entry.get("next_steps")
    if not templates:
        return None
    result = []
    for template in templates:
        step = {"command": template["command"], "when": template["when"]}
        static_argv = template.get("argv")
        if static_argv is not None:
            step["argv"] = list(static_argv)
        argv_template = template.get("argv_template")
        if argv_template is not None:
            argv = _build_argv(argv_template, template["command"], context)
            if argv is not None:
                step["argv"] = argv
        result.append(step)
    return result if result else None


def build_situation(command, status, guard=None):
    if guard is not None and guard in VERSION_MISMATCH_SITUATIONS:
        return VERSION_MISMATCH_SITUATIONS[guard]
    entry = GUIDANCE_MATRIX.get((command, status))
    if entry is None:
        return None
    return entry.get("situation")


def render_top_level_help():
    command_group_sections = []
    for title, commands in COMMAND_GROUPS:
        command_group_sections.append(
            "{}\n{}".format(title, _bullet_lines("{}: {}".format(name, TOP_LEVEL_COMMANDS[name]) for name in commands))
        )
    sections = [
        "Overview\nunity-puer-exec is the primary CLI surface for preparing Unity, executing JavaScript, observing long-running work, and checking session state.\nFor normal project-scoped tasks, start with `exec` and add observation commands only when the workflow needs them.\nLegacy aliases remain compatibility shims and are not authoritative command surfaces.",
        "Bridge Model\n`unity-puer-exec` script authoring uses a PuerTS-style JavaScript-to-C# bridge. Use `puer.loadType(...)` to load Unity or C# types, and do not assume bridged C# arrays or `List<T>` values behave exactly like native JS arrays.",
        "Recommended Path\n{}".format(_bullet_lines(RECOMMENDED_PATH)),
        "Command Groups\n{}".format("\n\n".join(command_group_sections)),
        "Global Options\n- `--version`: report the acting CLI build and exit, without a command and without contacting Unity. The CLI executable and the Unity Editor package ship as one release; when their versions disagree, commands refuse with `version_mismatch` and there is no bypass -- reconcile the installation instead.\n- `--suppress-guidance`: omit `next_steps` and `situation` from command responses. Status explanations remain available via `<command> --help-status`.\n- `--response-file <path>`: persist the complete normalized command response to a local file and print a compact reference (with `byte_count` and `sha256`) instead of the full JSON; use this when a response may exceed the caller's output budget. `wait-for-exec --response-file` can recover an already-completed large result by the same `request_id` without re-executing the script.",
        "Global Selector Rules\n- Use exactly one selector on commands that target a Unity session: `--project-path` or `--base-url`.\n- `--project-path` is the normal choice when the CLI should discover, launch, or recover Unity for a project.\n- `--base-url` is for a direct service you already know how to reach.",
        "Common Help Examples\nUse `unity-puer-exec --help-example <example-id>` to view full steps.\n{}".format(
            _bullet_lines(
                "`{}`: help-example id for `unity-puer-exec --help-example {}`; {}".format(
                    workflow_id,
                    workflow_id,
                    TOP_LEVEL_WORKFLOWS[workflow_id],
                )
                for workflow_id in WORKFLOW_IDS
            )
        ),
    ]
    return _join_sections(sections)


def render_command_help(command):
    info = COMMAND_HELP[command]
    sections = [
        "Quick Start\n{}".format(_bullet_lines(info["quick_start"])),
        "More Help\n{}".format(_bullet_lines(["`--help-args`", "`--help-status`"])),
        "Related Help Examples\n{}".format(
            _bullet_lines(
                "`{}`: use `unity-puer-exec --help-example {}`".format(item, item) for item in info["related_workflows"]
            )
        )
        if info["related_workflows"]
        else "Related Help Examples\n- none",
    ]
    return _join_sections(sections)


def render_command_args_help(command):
    info = COMMAND_HELP[command]["args"]
    sections = []
    for title in ("Arguments", "Selector Rules", "Bridge Model", "Script Context", "Range Rules", "Filter Rules", "Timeout Rules"):
        items = info.get(title)
        if items:
            sections.append("{}\n{}".format(title, _bullet_lines(items)))
    sections.append("Global Options\n{}".format(_bullet_lines([
        "`--suppress-guidance`: omit `next_steps` and `situation` from responses. Use `--help-status` as a fallback for status explanations.",
        "`--response-file <path>`: persist the complete normalized response to a local file and print a compact reference (`response_file.path`, `byte_count`, `sha256`) on the same stream instead of the full JSON. The command's exit code and stream selection are unchanged; if persistence fails, the original response is emitted with an additive `response_file_error` instead.",
    ])))
    return _join_sections(sections)


def render_command_status_help(command):
    info = COMMAND_HELP[command]["status"]
    success_lines = ["All success states exit with code `0`."] + list(info["success"])
    failure_lines = []
    for status, code, meaning in info["failure"]:
        line = "`{}` -> exit {}: {}".format(status, code, meaning)
        situation = build_situation(command, status)
        if situation:
            line += " Situation: {}".format(situation)
        failure_lines.append(line)
    failure_lines.append(VERSION_MISMATCH_STATUS_LINE)
    sections = [
        "Success Statuses\n{}".format(_bullet_lines(success_lines)),
        "Non-success Statuses\n{}".format(_bullet_lines(failure_lines)),
    ]
    if command in LOG_OFFSET_AWARE_COMMANDS:
        sections.append(
            "Log Offset Conditions\n{}".format(_bullet_lines(list(LOG_OFFSETS_INVALIDATED_HELP_LINES)))
        )
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
