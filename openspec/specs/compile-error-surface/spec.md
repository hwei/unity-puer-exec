# Compile Error Surface

## Purpose

Detect C# compilation errors and warnings in the Unity Editor via `CompilationPipeline` hooks, surface them through exec responses and dedicated CLI diagnostic commands, automatically dismiss Safe Mode dialogs, and ensure the agent sees a uniform `unity_compile_error` signal regardless of whether the server or Safe Mode produced the errors.

## Requirements

### Requirement: Unity server tracks per-compilation results

The Unity execution server SHALL subscribe to `CompilationPipeline.compilationStarted` and `CompilationPipeline.assemblyCompilationFinished`. It SHALL maintain counters for total errors and total warnings and SHALL store individual `CompilerMessage` entries in type-keyed collections protected by a lock. All state SHALL reset atomically when a new compilation starts.

#### Scenario: Compilation starts and resets state

- **WHEN** `CompilationPipeline.compilationStarted` fires
- **THEN** the server resets the error counter, warning counter, and both message collections to empty under lock
- **AND** the `_lastCompilationHadErrors` flag is set to false

#### Scenario: Assembly compiles with errors

- **WHEN** `CompilationPipeline.assemblyCompilationFinished` fires with one or more `CompilerMessage` entries of type `Error`
- **THEN** the error counter increments by the count of error messages
- **AND** each error message is appended to the error collection under lock
- **AND** the `_lastCompilationHadErrors` flag is set to true

#### Scenario: Assembly compiles with warnings only

- **WHEN** `CompilationPipeline.assemblyCompilationFinished` fires with `CompilerMessage` entries of type `Warning` and no errors
- **THEN** the warning counter increments and each warning is appended to the warning collection
- **AND** the `_lastCompilationHadErrors` flag remains false

#### Scenario: Multiple assemblies finish with mixed results

- **WHEN** assembly A finishes with errors and assembly B finishes with warnings only during the same compilation session
- **THEN** errors from A are collected and `_lastCompilationHadErrors` is true
- **AND** warnings from B are collected
- **AND** the state reflects the union of all messages across all assemblies in the session

### Requirement: Exec endpoint returns unity_compile_error when compilation had errors

When the `/exec` endpoint receives a valid execution request, the server SHALL check `_lastCompilationHadErrors` after the `IsCompilingOrReloading()` check and before JavaScript execution. When the flag is true, the server SHALL return `{"ok": false, "status": "unity_compile_error"}` with inline compile diagnostics instead of proceeding to execution.

#### Scenario: Exec with compile errors present

- **WHEN** a valid `/exec` request arrives
- **AND** `_lastCompilationHadErrors` is true
- **AND** the server is not currently compiling
- **THEN** the response has `ok: false` and `status: "unity_compile_error"`
- **AND** the response includes `compile_errors_total`, `compile_warnings_total`, and `compile_messages`
- **AND** JavaScript execution is not started

#### Scenario: Exec with no compile errors

- **WHEN** a valid `/exec` request arrives and `_lastCompilationHadErrors` is false
- **THEN** the server proceeds to the existing execution logic

#### Scenario: Compile error gate is checked after request parsing

- **WHEN** `/exec` receives a request with `refresh_before_exec: true`
- **THEN** the server handles the refresh path first (triggers `AssetDatabase.Refresh()` and returns)
- **AND** the compile error gate is skipped for refresh requests

### Requirement: Wait-for-exec endpoint returns unity_compile_error

The `/wait-for-exec` endpoint SHALL also check `_lastCompilationHadErrors` before looking up the job by request_id. When the flag is true, it SHALL return `unity_compile_error` with the same inline message structure as `/exec`.

#### Scenario: Wait-for-exec with compile errors present

- **WHEN** a caller sends `/wait-for-exec` for any request_id
- **AND** `_lastCompilationHadErrors` is true
- **THEN** the response has `status: "unity_compile_error"` with inline compile diagnostics
- **AND** the server does not attempt to look up or wait on the job

### Requirement: refresh_before_exec triggers native AssetDatabase.Refresh

The `ExecRequest` protocol SHALL accept a `refresh_before_exec` boolean field (default false). When true, the server SHALL enqueue `AssetDatabase.Refresh()` on the main thread via `MainThreadActions`, await its completion, and return a confirmation response without executing JavaScript.

#### Scenario: Refresh-before-exec is requested

- **WHEN** `/exec` receives a request with `refresh_before_exec: true`
- **THEN** the server calls `AssetDatabase.Refresh()` on the main thread
- **AND** the server returns `{"ok": true, "status": "completed", "result": {"refreshed": true}}`
- **AND** no JavaScript execution occurs

#### Scenario: Refresh-before-exec bypasses the compile error gate

- **WHEN** `/exec` receives a request with `refresh_before_exec: true`
- **AND** `_lastCompilationHadErrors` is true from a prior compilation
- **THEN** the server still performs the refresh
- **AND** the compile error gate (which would normally block execution) is not applied to the refresh request

### Requirement: Exec responses include inline compile messages

When the server returns `unity_compile_error` from `/exec` or `/wait-for-exec`, the response SHALL include `compile_messages` as an array of up to 3 message objects, with errors prioritized over warnings. Each message SHALL include `type` ("error" or "warning"), `message`, `file`, `line`, and `column`.

#### Scenario: Errors prioritized in inline messages

- **WHEN** there are 2 errors and 3 warnings
- **THEN** `compile_messages` contains the 2 errors plus 1 warning (3 total)

#### Scenario: Message includes file location

- **WHEN** a `CompilerMessage` has `file`, `line`, and `column`
- **THEN** the serialized object includes those fields with 1-based line and column values

### Requirement: Server exposes /get-compile-errors endpoint

The server SHALL expose a `/get-compile-errors` endpoint accepting `start` (int, default 0) and `count` (int, default 3, clamped to [1, 100]). The response SHALL include `total`, `start`, `returned`, `messages`, and `session_marker`.

#### Scenario: Retrieve first 3 errors

- **WHEN** a caller sends `{"start": 0, "count": 3}` to `/get-compile-errors` with 7 total errors
- **THEN** the response has `total: 7`, `returned: 3`, and `messages` with 3 entries

#### Scenario: Retrieve beyond available range

- **WHEN** a caller sends `{"start": 10, "count": 3}` with 7 total errors
- **THEN** the response has `returned: 0` and `messages: []`

#### Scenario: Response includes session_marker

- **WHEN** `/get-compile-errors` returns a response
- **THEN** the response includes `session_marker` matching the server's current session marker

### Requirement: Server exposes /get-compile-warnings endpoint

The server SHALL expose a `/get-compile-warnings` endpoint with the same request and response structure as `/get-compile-errors`, operating on the warning collection.

#### Scenario: Retrieve warnings with session_marker

- **WHEN** a caller sends `{"start": 0, "count": 5}` to `/get-compile-warnings`
- **THEN** the response includes `messages`, `total`, `returned`, and `session_marker`

### Requirement: Non-exec endpoints remain available during compile errors

The `/health`, `/get-compile-errors`, `/get-compile-warnings`, `/reset-jsenv`, and other non-exec endpoints SHALL remain available regardless of `_lastCompilationHadErrors`.

#### Scenario: Health returns ready despite compile errors

- **WHEN** `_lastCompilationHadErrors` is true
- **AND** the server is otherwise running
- **THEN** `/health` returns `{"ok": true, "status": "ready"}` with the usual session fields

### Requirement: Exit code 23 represents unity_compile_error

The CLI SHALL define `EXIT_UNITY_COMPILE_ERROR = 23`. When the server returns `status: "unity_compile_error"`, the CLI SHALL map this to exit code 23 and include the compile diagnostics in the stdout payload.

#### Scenario: exec returns exit code 23

- **WHEN** the server returns `status: "unity_compile_error"` for an `/exec` request
- **THEN** the CLI exits with code 23
- **AND** stdout includes `compile_errors_total`, `compile_warnings_total`, and `compile_messages`

### Requirement: CLI exposes get-compile-errors and get-compile-warnings commands

The CLI SHALL expose `get-compile-errors` and `get-compile-warnings` commands accepting `--project-path`/`--base-url` selectors and optional `--start` (int, default 0) and `--count` (int, default 3, validated to [1, 100]). The commands SHALL post to the corresponding server endpoints and return structured JSON results including `session_marker`.

#### Scenario: Retrieve compile errors for a project

- **WHEN** a caller invokes `get-compile-errors --project-path X:/proj --start 0 --count 10`
- **THEN** the command returns `result.total`, `result.returned`, `result.messages`, and `result.session_marker`

#### Scenario: Count validation rejects out-of-range values

- **WHEN** a caller invokes `get-compile-errors --count 0` or `--count 101`
- **THEN** the command raises a usage error before contacting the server

#### Scenario: Start validation rejects negative values

- **WHEN** a caller invokes `get-compile-errors --start -1`
- **THEN** the command raises a usage error before contacting the server

### Requirement: Safe Mode dialog is auto-dismissed via keyboard

When the CLI detects the "Enter Safe Mode?" dialog during exec, it SHALL dismiss it by sending an Enter key to activate the default button, using `SetForegroundWindow` to bring the dialog to the foreground followed by `keybd_event(VK_RETURN)`. This approach SHALL be DPI-independent.

#### Scenario: Safe Mode dialog is detected and dismissed

- **WHEN** exec detects the "Enter Safe Mode?" dialog via `list_supported_modal_blockers`
- **THEN** the CLI calls `resolve_modal_blocker` with `action: "cancel"`
- **AND** `_click_cancel_button` dispatches to `_click_via_keyboard` based on `click_method: "keyboard"`
- **AND** `_click_via_keyboard` brings the dialog to foreground and sends Enter

#### Scenario: Safe Mode dialog resolution is confirmed

- **WHEN** the CLI sends Enter to dismiss the Safe Mode dialog
- **THEN** the CLI polls for dialog disappearance before reporting success
- **AND** the resolution result follows the existing `resolve_modal_blocker` contract

### Requirement: Safe Mode is transparent to the agent

When Unity is in Safe Mode (either the dialog is showing or the main window title contains "SAFE MODE"), the CLI SHALL surface `unity_compile_error` to the agent rather than `modal_blocked`. The agent SHALL never see `status: "modal_blocked"` or `safe_mode_dialog` as a blocker type.

#### Scenario: Agent receives unity_compile_error during Safe Mode

- **WHEN** `_normalize_exec_blocker_result` detects a `safe_mode_dialog` blocker
- **THEN** the CLI auto-dismisses the dialog
- **AND** the CLI extracts compile errors from the Editor log via `_extract_compile_errors_from_log`
- **AND** the CLI returns `status: "unity_compile_error"` with exit code 23
- **AND** the response includes the extracted compile errors

#### Scenario: Safe Mode state detected from window title

- **WHEN** the Safe Mode dialog has already been dismissed but the main Unity window title shows "SAFE MODE"
- **THEN** `list_supported_modal_blockers` still reports `safe_mode_dialog` as a blocker type
- **AND** exec normalization treats it as a compile error, not a modal blocker

### Requirement: Compile errors are extracted from Editor log during Safe Mode

When the Unity server is not running (Safe Mode), the CLI SHALL extract C# compile errors from the Editor log file using regex matching. The extraction SHALL handle standard `file(line,col): error [CODE]: message` formats, optional error codes, multi-line continuation messages, and Windows absolute paths.

#### Scenario: Standard error extracted from log

- **WHEN** the Editor log contains `Assets/Foo.cs(10,5): error CS1003: Syntax error`
- **THEN** `_extract_compile_errors_from_log` returns an error with `file: "Assets/Foo.cs"`, `line: 10`, `column: 5`, `code: "CS1003"`, and the message text

#### Scenario: Uncoded error extracted from log

- **WHEN** the Editor log contains `Packages/com.x/Editor/Foo.cs(3,1): error : Some message`
- **THEN** the extracted error has `code: null` and `message: "Some message"` (leading ": " stripped)

#### Scenario: Multi-line error message collected

- **WHEN** an error line is followed by indented continuation lines
- **THEN** the continuation lines are appended to the error message

#### Scenario: No errors in log

- **WHEN** the Editor log contains no lines matching the error pattern
- **THEN** `_extract_compile_errors_from_log` returns `None`

### Requirement: CLI brings Unity to foreground on every exec

Before submitting an exec request in project-path mode, the CLI SHALL bring the Unity Editor main window to the foreground via `SetForegroundWindow`. This ensures Unity detects file system changes and triggers recompilation.

#### Scenario: Unity window brought to foreground

- **WHEN** `run_exec` or `run_wait_for_exec` is called in project-path mode
- **THEN** `_bring_unity_to_foreground` is called before any server interaction
- **AND** `_foreground_unity_window` locates the main Unity window by PID and window title
- **AND** `SetForegroundWindow` is called on the found window handle

#### Scenario: Foreground call is non-fatal on failure

- **WHEN** `_bring_unity_to_foreground` encounters any exception (e.g., window not found, API failure)
- **THEN** the exception is silently caught and execution continues

### Requirement: Session marker in get-compile responses enables stable pagination

The `/get-compile-errors` and `/get-compile-warnings` server responses SHALL include `session_marker`. The CLI SHALL extract and surface this marker in command results. This enables the agent to detect domain reloads between paginated calls and avoid using stale index offsets.

#### Scenario: Marker matches between exec and get-compile-errors

- **WHEN** an agent receives `unity_compile_error` from exec with `session_marker: "abc123"`
- **AND** subsequently calls `get-compile-errors`
- **THEN** the `get-compile-errors` result includes `session_marker: "abc123"`
- **AND** the agent can confirm the error list has not been reset by a domain reload

#### Scenario: Marker changes after domain reload

- **WHEN** a domain reload occurs (e.g., after successful recompilation)
- **THEN** the server generates a new `session_marker`
- **AND** subsequent `get-compile-errors` responses carry the new marker
- **AND** the agent can detect the list has been refreshed and reset pagination
