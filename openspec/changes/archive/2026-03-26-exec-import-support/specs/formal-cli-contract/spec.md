## MODIFIED Requirements

### Requirement: `exec` is the primary work command

`exec` SHALL send JavaScript to the Unity-side execution service. It SHALL accept exactly one selector and exactly one script input source. In project-path mode it MAY implicitly prepare Unity enough to satisfy the request. In base-url mode it SHALL target an already chosen service without owning Unity launch. When project-path mode needs to prepare Unity, it SHALL follow the same duplicate-launch avoidance and project-scoped recovery rules as `wait-until-ready`. If project-scoped execution is blocked by a Unity-native modal dialog, the CLI SHALL surface a machine-usable blocking result or blocker diagnostics instead of failing only as an unexplained timeout.

Entry scripts SHALL be valid ES modules and MAY contain static `import` declarations. When `--file` is used, relative imports are resolved from the source file's directory. When `--code` or `--stdin` is used with `--import-base-url`, imports are resolved from the provided base. When `--code` or `--stdin` is used without `--import-base-url` and the submitted code contains an `import` declaration, the command SHALL return a machine-readable error.

The `exec` command SHALL accept the following optional arguments in addition to the existing surface:
- `--import-base-url <value>`: sets the import resolution base (filesystem path or HTTP/HTTPS URL).
- `--reset-jsenv-before-exec`: disposes and recreates the JsEnv singleton before executing, clearing the JS module cache.

#### Scenario: Project-scoped execution is requested
- **WHEN** `exec --project-path ...` is invoked with valid script input
- **THEN** the command may prepare Unity as needed for the execution request
- **AND** the command returns either `status = "completed"` or `status = "running"`

#### Scenario: Project-scoped exec encounters an already-open target project
- **WHEN** `exec --project-path ...` needs readiness work for a project that already has an open or recovering Unity Editor instance
- **THEN** the CLI applies the same project-scoped reuse or conflict behavior as `wait-until-ready`
- **AND** it does not initiate a blind second launch for the same project

#### Scenario: Project-scoped exec is blocked by a modal dialog
- **WHEN** `exec --project-path ...` cannot proceed because Unity Editor is blocked by a native modal dialog
- **THEN** the CLI surfaces a machine-usable blocking result or explicit blocker diagnostics
- **AND** the caller does not need to guess whether the failure was caused by script logic or editor UI state

#### Scenario: Caller queries blocker state after an exec-side stall
- **WHEN** a caller invokes the explicit blocker-query command for a project-scoped Unity Editor instance after an exec-side timeout or stall symptom
- **THEN** the command reports whether a supported modal blocker is currently detected
- **AND** the command does not require the caller to resubmit the blocked exec request

#### Scenario: Supported save-scene blockers are reported with stable types
- **WHEN** project-scoped exec or blocker-query detection observes the supported Windows save-scene dialogs
- **THEN** the machine-readable payload uses `status = "modal_blocked"`
- **AND** `blocker.type` is `save_modified_scenes_prompt` for the `Scene(s) Have Been Modified` dialog
- **AND** `blocker.type` is `save_scene_dialog` for the `Save Scene` file-save dialog
- **AND** `blocker.scope` is `exec`

#### Scenario: Entry script with imports is executed via --file
- **WHEN** `exec --file entry.js` is invoked and `entry.js` contains static `import` declarations
- **THEN** the command resolves imports relative to `entry.js`'s directory and executes successfully

#### Scenario: Code mode with imports requires --import-base-url
- **WHEN** `exec --code "import {x} from './lib.js'; ..."` is invoked without `--import-base-url`
- **THEN** the command returns a failed result with `error = "missing_import_base_url"`

## ADDED Requirements

### Requirement: ExecRequest protocol carries optional import context fields
The exec HTTP request payload SHALL accept three optional fields alongside the existing `request_id`, `code`, and `wait_timeout_ms`:
- `source_path` (string): absolute path of the entry file; populated automatically by the CLI when `--file` is used.
- `import_base_url` (string): import resolution base; populated when `--import-base-url` is provided.
- `reset_jsenv_before_exec` (bool): when true, the server resets the JsEnv before evaluating; populated when `--reset-jsenv-before-exec` is set.

These fields are optional. Requests that omit them retain the existing behavior.

#### Scenario: --file populates source_path automatically
- **WHEN** `exec --file /scripts/entry.js` is invoked
- **THEN** the CLI includes `source_path = "/scripts/entry.js"` in the payload without requiring the caller to pass it explicitly

#### Scenario: Payload without new fields behaves as before
- **WHEN** an exec payload omits `source_path`, `import_base_url`, and `reset_jsenv_before_exec`
- **THEN** the server executes using the prior behavior
- **AND** scripts without `import` declarations execute as before
