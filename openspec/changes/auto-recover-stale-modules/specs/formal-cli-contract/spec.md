## ADDED Requirements

### Requirement: Exec stale-module policy controls automatic recovery

The formal CLI SHALL accept `--stale-module-policy` with values `auto-reset` and `error`. The default SHALL be `auto-reset`. The CLI SHALL carry the effective policy through immediate submission, pending-exec persistence, refresh/compile continuation, and resumed submission. Help SHALL explain that `error` preserves the current JsEnv for callers that depend on `ctx.globals` or module singleton state.

#### Scenario: Omitted policy defaults to auto-reset

- **WHEN** an agent invokes `exec` without `--stale-module-policy`
- **THEN** the effective request policy is `auto-reset`

#### Scenario: Invalid policy fails before submission

- **WHEN** an agent supplies a stale-module policy other than `auto-reset` or `error`
- **THEN** the CLI returns a usage error without submitting an exec request

#### Scenario: Running continuation preserves policy

- **WHEN** project startup or refresh causes an exec request using `--stale-module-policy error` to be persisted as pending
- **THEN** the later resumed submission still carries `stale_module_policy = "error"`

### Requirement: Exec responses disclose JsEnv reset recovery

When the server performs an exec-scoped JsEnv reset, the terminal exec response SHALL contain `recovery.performed = true`, `recovery.type = "jsenv_reset"`, `recovery.reason`, `recovery.policy`, and a sorted `recovery.affected_modules` array. `recovery.reason` SHALL be `module_cache_stale` for automatic stale recovery and `explicit_request` for `--reset-jsenv-before-exec`. An exec response for which no reset occurred SHALL omit `recovery`. Recovery metadata SHALL be identical whether returned by `exec` synchronously or later by `wait-for-exec`.

#### Scenario: Automatic recovery is visible

- **WHEN** default-policy exec detects stale local modules and completes after resetting the JsEnv
- **THEN** the response reports `recovery.reason = "module_cache_stale"`
- **AND** `recovery.affected_modules` contains the normalized paths that triggered reset

#### Scenario: Explicit reset is visible without stale modules

- **WHEN** an exec using `--reset-jsenv-before-exec` completes and no tracked module was stale
- **THEN** the response reports `recovery.reason = "explicit_request"`
- **AND** `recovery.affected_modules` is an empty array

#### Scenario: Wait returns the accepted job recovery evidence

- **WHEN** a recovered exec first returns `running` and the caller later invokes `wait-for-exec`
- **THEN** the terminal response contains the same recovery metadata stored with the accepted job

## MODIFIED Requirements

### Requirement: ExecRequest protocol carries optional import context fields

The exec HTTP request payload SHALL accept four optional fields alongside the existing `request_id`, `code`, and `wait_timeout_ms`:
- `source_path` (string): absolute path of the entry file; populated automatically by the CLI when `--file` is used.
- `import_base_url` (string): import resolution base; populated when `--import-base-url` is provided.
- `reset_jsenv_before_exec` (bool): when true, the server resets the JsEnv before evaluating; populated when `--reset-jsenv-before-exec` is set.
- `stale_module_policy` (string): `auto-reset` or `error`; omission SHALL mean `auto-reset`.

Requests that omit the first three fields retain their existing import-context behavior. A request that omits `stale_module_policy` adopts the new default automatic stale recovery behavior.

#### Scenario: --file populates source_path automatically

- **WHEN** `exec --file /scripts/entry.js` is invoked
- **THEN** the CLI includes `source_path = "/scripts/entry.js"` in the payload without requiring the caller to pass it explicitly

#### Scenario: Payload without policy uses server default

- **WHEN** an exec payload omits `stale_module_policy`
- **THEN** the server treats the request as `stale_module_policy = "auto-reset"`

#### Scenario: Invalid protocol policy is rejected

- **WHEN** a direct HTTP client submits a non-empty `stale_module_policy` other than `auto-reset` or `error`
- **THEN** the server returns a machine-readable validation failure without executing code or resetting the JsEnv

### Requirement: Exec reports module_cache_stale when file mtime has changed

The formal CLI SHALL expose `module_cache_stale` as a documented non-success status for `exec` when one or more loaded local modules changed or were removed and the effective policy is `error`. The CLI SHALL provide a `situation` explanation, the affected module paths, and `next_steps` candidates including a concrete argv for re-running with `--reset-jsenv-before-exec` and guidance for using `auto-reset`. Under the default policy, the same stale condition SHALL instead produce an accepted exec whose terminal response discloses recovery.

#### Scenario: Agent receives module_cache_stale under error policy

- **WHEN** `exec --file` is invoked with `--stale-module-policy error`
- **AND** a local module loaded by the current JsEnv has changed or been removed
- **THEN** the response has `status = "module_cache_stale"`
- **AND** `ok` is `false`
- **AND** the response identifies all affected tracked module paths
- **AND** `next_steps` includes explicit reset and automatic recovery choices

#### Scenario: Default policy recovers instead of returning stale status

- **WHEN** the same stale condition is detected with omitted or explicit `auto-reset` policy
- **THEN** `exec` does not return `module_cache_stale`
- **AND** the accepted job resets once before evaluation and reports recovery in its terminal response

#### Scenario: module_cache_stale appears in --help-status

- **WHEN** an agent invokes `unity-puer-exec exec --help-status`
- **THEN** `module_cache_stale` is listed as the `error`-policy non-success status with its exit code and situation explanation
