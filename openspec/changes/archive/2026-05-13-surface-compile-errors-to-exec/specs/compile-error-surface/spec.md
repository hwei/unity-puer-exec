# Compile Error Surface

## Purpose

Detect C# compilation errors and warnings in the Unity Editor via `CompilationPipeline` hooks, and surface them through exec responses and dedicated CLI diagnostic commands so the agent can discover and address C# compilation issues early.

## ADDED Requirements

### Requirement: Unity server tracks per-session compilation results

The Unity execution server SHALL subscribe to `CompilationPipeline.compilationStarted` and `CompilationPipeline.assemblyCompilationFinished`. It SHALL maintain per-session counters for total errors and total warnings, and SHALL store individual `CompilerMessage` entries in collections keyed by type (error / warning).

#### Scenario: Compilation starts and resets state

- **WHEN** `CompilationPipeline.compilationStarted` fires
- **THEN** the server resets the error counter, warning counter, and message collections to empty
- **AND** the `_lastCompilationHadErrors` flag is set to false

#### Scenario: Assembly compiles with errors

- **WHEN** `CompilationPipeline.assemblyCompilationFinished` fires with one or more `CompilerMessage` entries of type `Error`
- **THEN** the error counter increments by the count of error messages
- **AND** each error message is appended to the error collection
- **AND** the `_lastCompilationHadErrors` flag is set to true

#### Scenario: Assembly compiles with warnings only

- **WHEN** `CompilationPipeline.assemblyCompilationFinished` fires with `CompilerMessage` entries of type `Warning` and no errors
- **THEN** the warning counter increments by the count of warning messages
- **AND** each warning message is appended to the warning collection
- **AND** the `_lastCompilationHadErrors` flag remains false

#### Scenario: Assembly compiles with no messages

- **WHEN** `CompilationPipeline.assemblyCompilationFinished` fires with an empty or null messages array
- **THEN** no counters change and no messages are stored

### Requirement: Exec endpoint returns unity_compile_error when compilation had errors

When the `/exec` endpoint receives a valid execution request and the server's `_lastCompilationHadErrors` flag is true, the server SHALL return `{"ok": false, "status": "unity_compile_error"}` instead of proceeding to JavaScript execution. The response SHALL include `compile_errors_total`, `compile_warnings_total`, and `compile_messages` (up to 3 messages, errors prioritized).

#### Scenario: Exec is invoked with compile errors present

- **WHEN** a valid `/exec` request arrives
- **AND** `_lastCompilationHadErrors` is true
- **AND** the server is not currently compiling (`IsCompilingOrReloading()` is false, which is checked first)
- **THEN** the response has `ok: false` and `status: "unity_compile_error"`
- **AND** the response includes `compile_errors_total` as a positive integer
- **AND** the response includes `compile_warnings_total` as a non-negative integer
- **AND** the response includes `compile_messages` as an array of up to 3 message objects
- **AND** JavaScript execution is not started

#### Scenario: Exec is invoked with no compile errors

- **WHEN** a valid `/exec` request arrives
- **AND** `_lastCompilationHadErrors` is false
- **THEN** the server proceeds to the existing execution logic (no `unity_compile_error` response)

#### Scenario: Exec returns compile errors inline with errors prioritized

- **WHEN** the response includes `compile_messages`
- **AND** there are at least one error and at least one warning
- **THEN** errors appear before warnings in the `compile_messages` array
- **AND** the total count of entries in `compile_messages` does not exceed 3

### Requirement: Each compile message includes standard fields

Each entry in `compile_messages` and in the ranged retrieval endpoints SHALL include `type` (string: `"error"` or `"warning"`), `message` (string: compiler message text), `file` (string: source file path), `line` (int: 1-based line number), and `column` (int: 1-based column number).

#### Scenario: Compile message carries file location

- **WHEN** a `CompilerMessage` has `file`, `line`, and `column` values
- **THEN** the serialized message object includes those fields with the same values
- **AND** `line` and `column` are 1-based

#### Scenario: Compile message has missing file location

- **WHEN** a `CompilerMessage` has an empty or null `file` field
- **THEN** the serialized `file` field is an empty string
- **AND** `line` and `column` default to 0

### Requirement: Server exposes get-compile-errors endpoint

The server SHALL expose a `/get-compile-errors` endpoint that accepts optional `start` (int, default 0) and `count` (int, default 3, max 100) query parameters. The response SHALL return a JSON object with `messages` (array of error message objects, possibly empty), `total` (int: total error count), and `returned` (int: number of messages in this response).

#### Scenario: Retrieve first 3 errors

- **WHEN** a caller sends `POST /get-compile-errors` with body `{"start": 0, "count": 3}`
- **AND** there are 7 total errors
- **THEN** the response includes `total: 7`, `returned: 3`, and `messages` with 3 entries

#### Scenario: Retrieve errors beyond available range

- **WHEN** a caller sends `POST /get-compile-errors` with body `{"start": 10, "count": 3}`
- **AND** there are 7 total errors
- **THEN** the response includes `total: 7`, `returned: 0`, and `messages` as an empty array

#### Scenario: Default count applies when count is omitted

- **WHEN** a caller sends `POST /get-compile-errors` with body `{"start": 0}`
- **THEN** the endpoint uses a default count of 3

### Requirement: Server exposes get-compile-warnings endpoint

The server SHALL expose a `/get-compile-warnings` endpoint that accepts optional `start` (int, default 0) and `count` (int, default 3, max 100) query parameters. The response format SHALL mirror `/get-compile-errors`: `messages`, `total`, and `returned`.

#### Scenario: Retrieve warnings by range

- **WHEN** a caller sends `POST /get-compile-warnings` with body `{"start": 0, "count": 5}`
- **AND** there are 2 total warnings
- **THEN** the response includes `total: 2`, `returned: 2`, and `messages` with 2 entries

### Requirement: Wait-for-exec endpoint returns unity_compile_error

The `/wait-for-exec` endpoint SHALL also check `_lastCompilationHadErrors` when the requested job is not yet terminal, and return `unity_compile_error` with the same inline message structure as `/exec`.

#### Scenario: Wait-for-exec encounters compile errors

- **WHEN** a caller sends a `/wait-for-exec` request for a pending job
- **AND** `_lastCompilationHadErrors` is true
- **THEN** the response has `status: "unity_compile_error"` with inline compile diagnostics
- **AND** the response does not wait for the job to complete

### Requirement: Compile errors do not prevent non-exec operations

The `unity_compile_error` status SHALL only gate `/exec` and `/wait-for-exec`. The `/health`, `/get-compile-errors`, `/get-compile-warnings`, `/reset-jsenv`, and other endpoints SHALL remain available regardless of compilation state.

#### Scenario: Health check succeeds despite compile errors

- **WHEN** `_lastCompilationHadErrors` is true
- **AND** the server is otherwise running and not currently compiling
- **THEN** `/health` returns `{"ok": true, "status": "ready"}` with the usual session fields
