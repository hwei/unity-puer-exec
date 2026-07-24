## MODIFIED Requirements

### Requirement: Project-scoped launch supports a caller-controlled Editor log path

When `unity-puer-exec` launches Unity for a project-scoped workflow, the CLI SHALL support a caller-controlled path for the Unity Editor log so launch-driven sessions can intentionally avoid the default log location. When no caller-controlled path is supplied, the CLI SHALL still avoid the platform default per-user log location and launch the Editor against a log private to the target project, so an unrelated Editor cannot share the log the session is observed through.

#### Scenario: Caller requests a custom log file during launch

- **WHEN** a caller invokes a launch-driven command with `--unity-log-path <path>`
- **THEN** Unity is launched with that log-path override

#### Scenario: Launch without an explicit log path still isolates the Editor log

- **WHEN** a caller invokes a launch-driven command without `--unity-log-path`
- **THEN** Unity is launched against a log location private to the target project

## ADDED Requirements

### Requirement: Project-scoped launch accepts extra Unity argv tokens

When `unity-puer-exec` cold-starts Unity for a project-scoped workflow, the CLI SHALL forward caller-supplied extra argv tokens to the Unity process so a project that needs host-specific Unity switches can be launched under CLI control.

Extra tokens SHALL be accepted from either or both of:

- a repeatable project-path-mode flag `--unity-launch-arg <token>`, each occurrence one argv token
- the process environment variable `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS`, whose value is a JSON array of strings

Ambient tokens SHALL be applied first, then flag tokens; exact-token duplicates SHALL be collapsed. Extra tokens SHALL be appended after the CLI-owned launch arguments (`-projectPath`, the control-service activation switch, and the effective `-logFile`).

Tokens that rebind a CLI-owned switch — `-projectPath`, `-logFile`, or `-unityPuerExecControl` (case insensitive) — SHALL be rejected as a usage error rather than applied. An invalid ambient JSON value SHALL be rejected with a machine-usable reason rather than partially applied.

Extra tokens SHALL apply only when this CLI performs a cold launch. When the CLI attaches to an already-running Editor, supplied tokens SHALL be ignored and SHALL NOT by themselves cause the command to fail. The flag SHALL be valid only in project-path mode; supplying it with `--base-url` SHALL be a usage error.

#### Scenario: Caller supplies a host-required Unity switch on launch

- **WHEN** a project-scoped launch-driven command is invoked with `--unity-launch-arg -force-gles30` and no Editor is yet serving the project
- **THEN** the launched Unity process receives `-force-gles30` among its argv tokens
- **AND** the token appears after the CLI-owned `-projectPath`, activation switch, and `-logFile` arguments

#### Scenario: Ambient env supplies launch tokens without a per-command flag

- **WHEN** `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` is set to a JSON array such as `["-force-gles30"]`
- **AND** a project-scoped command cold-starts Unity without `--unity-launch-arg`
- **THEN** the launched Unity process receives those ambient tokens

#### Scenario: Flag and ambient tokens merge without duplicating exact matches

- **WHEN** the ambient variable and `--unity-launch-arg` both contribute the same token
- **THEN** the launched argv contains that token once

#### Scenario: CLI-owned switches cannot be rebound by passthrough

- **WHEN** a caller supplies `--unity-launch-arg -projectPath` or an ambient token equal to `-logFile` or `-unityPuerExecControl` (any case)
- **THEN** the command fails as a usage error before Unity is launched
- **AND** the error states that those switches are owned by the CLI

#### Scenario: Invalid ambient JSON is rejected

- **WHEN** `UNITY_PUER_EXEC_UNITY_LAUNCH_ARGS` is set to a value that is not a JSON array of strings
- **THEN** a launch-driven command fails with a machine-usable reason naming the variable
- **AND** Unity is not launched with a partial or guessed token list

#### Scenario: Passthrough tokens are ignored on attach

- **WHEN** a project-scoped command finds a controlled Editor already serving the project
- **AND** the caller also supplied `--unity-launch-arg` tokens
- **THEN** the command attaches without launching
- **AND** it does not fail solely because the tokens were supplied

#### Scenario: Passthrough flag is project-path only

- **WHEN** a caller supplies `--unity-launch-arg` together with `--base-url`
- **THEN** the command fails as a usage error
- **AND** it does not target the supplied base URL
