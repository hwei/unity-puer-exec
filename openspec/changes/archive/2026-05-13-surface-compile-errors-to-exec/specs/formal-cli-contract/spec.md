# Formal CLI Contract (delta)

## ADDED Requirements

### Requirement: Exit code 23 represents unity_compile_error

The CLI SHALL define exit code 23 (`EXIT_UNITY_COMPILE_ERROR`). When the Unity execution service returns `status: "unity_compile_error"`, the CLI SHALL map this to exit code 23 and SHALL include the inline compile diagnostics in the response payload.

#### Scenario: exec returns unity_compile_error exit code

- **WHEN** the Unity server returns `status: "unity_compile_error"` for an `/exec` request
- **THEN** the CLI exits with code 23
- **AND** the stdout JSON includes `compile_errors_total`, `compile_warnings_total`, and `compile_messages`

#### Scenario: base-url mode returns unity_compile_error exit code

- **WHEN** `exec --base-url ...` receives `status: "unity_compile_error"`
- **THEN** the CLI exits with code 23 and includes the compile diagnostics in stdout

### Requirement: get-compile-errors command retrieves error details

The CLI SHALL expose a `get-compile-errors` command that accepts `--project-path` (required for project-scoped sessions) or `--base-url`, and optional `--start` (int, default 0) and `--count` (int, default 3, max 100) arguments. The command SHALL post to `/get-compile-errors` and return the response as structured JSON.

#### Scenario: Retrieve first 10 compile errors for a project

- **WHEN** a caller invokes `unity-puer-exec get-compile-errors --project-path X:/project --start 0 --count 10`
- **AND** the Unity server has recorded compile errors
- **THEN** the command returns `ok: true` with `result` containing `total`, `returned`, and `messages`
- **AND** `messages` is an array of error message objects with `type`, `message`, `file`, `line`, and `column`

#### Scenario: Get compile errors with no errors recorded

- **WHEN** a caller invokes `unity-puer-exec get-compile-errors --project-path X:/project`
- **AND** no compilation has occurred or the last compilation had no errors
- **THEN** the command returns `ok: true` with `result.total: 0`, `result.returned: 0`, and `result.messages: []`

#### Scenario: get-compile-errors uses default count

- **WHEN** a caller invokes `get-compile-errors` without `--count`
- **THEN** the command uses a default count of 3

### Requirement: get-compile-warnings command retrieves warning details

The CLI SHALL expose a `get-compile-warnings` command with the same argument structure and behavior as `get-compile-errors`, posting to `/get-compile-warnings`.

#### Scenario: Retrieve compile warnings for a project

- **WHEN** a caller invokes `unity-puer-exec get-compile-warnings --project-path X:/project --start 0 --count 5`
- **AND** the last compilation produced warnings
- **THEN** the command returns `ok: true` with `result.messages` containing warning message objects

### Requirement: get-compile-errors and get-compile-warnings support direct base-url mode

Both `get-compile-errors` and `get-compile-warnings` SHALL support `--base-url` as an alternative selector to `--project-path`, following the existing selector rules.

#### Scenario: Retrieve compile errors via direct base URL

- **WHEN** a caller invokes `unity-puer-exec get-compile-errors --base-url http://127.0.0.1:55231`
- **THEN** the command targets the specified URL directly
- **AND** the response format is identical to the project-path case

### Requirement: get-compile-errors and get-compile-warnings count is validated

The `--count` parameter for both commands SHALL reject values less than 1 or greater than 100 as usage errors.

#### Scenario: Count exceeds maximum

- **WHEN** a caller invokes `get-compile-errors --count 200`
- **THEN** the command returns a usage error before contacting the server

### Requirement: get-compile-errors and get-compile-warnings start is validated

The `--start` parameter for both commands SHALL reject negative values as usage errors.

#### Scenario: Start is negative

- **WHEN** a caller invokes `get-compile-errors --start -5`
- **THEN** the command returns a usage error before contacting the server
