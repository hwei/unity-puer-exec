## REMOVED Requirements

### Requirement: Refresh-before-exec is a single refresh-settle-execute lifecycle

**Reason**: The flag carried three jobs and none survives. (1) Making a C# edit visible before the next exec is now automatic under `import-change-refresh`. (2) Forcing a refresh during play mode was never achievable — Unity defers all compilation until play mode exits — so the flag made a promise it could not keep. (3) Triggering recompilation after fixing compile errors was redundant, because fixing a C# error is itself a file write that the automatic refresh observes. Removing it also deletes the JS-side refresh template, the synthesized refresh request, and a dead condition at `UnityPuerExecServer.cs:640` where `!request.refresh_before_exec` was always true after the early return for the true case.

**Migration**: Drop the flag. To make a code change visible before the next exec, no action is needed — the refresh is automatic. To recompile after fixing C# errors, simply re-run `exec`; the fix's own file write is the trigger. To refresh non-code assets, which are deliberately not watched, call `AssetDatabase.Refresh()` through the bridge. A caller that still passes the flag receives a `usage error` with a `situation` explaining the removal, following the same removal treatment as `--include-log-offset`.

## MODIFIED Requirements

### Requirement: Direct base-url mode remains explicit

Base-url selector mode SHALL continue to target the caller-supplied endpoint directly. Direct mode SHALL NOT require project artifact validation and SHALL NOT imply Unity launch ownership. When the server reports that it triggered an automatic refresh before an exec, the CLI SHALL settle the resulting compilation cycle by re-probing the same caller-supplied endpoint rather than performing project-scoped re-acquisition. Automatic refresh SHALL be compatible with the direct-mode boundary: it is a server-side decision reported in the exec response, not a CLI-side launch or ownership action.

#### Scenario: Caller supplies base-url

- **WHEN** a selector-driven command is invoked with `--base-url <url>`
- **THEN** the command targets that URL directly according to the existing direct-service command boundary
- **AND** it does not rewrite the endpoint from a project-local session artifact

#### Scenario: Base-url caller requests refresh-before-exec

- **WHEN** a caller invokes `exec --base-url <url>` and the server reports an automatic refresh for a pending code change
- **THEN** the CLI settles the compile cycle by re-probing that same endpoint before running the user script
- **AND** it does not launch Unity or rewrite the endpoint from a session artifact

#### Scenario: Base-url caller with no pending change

- **WHEN** a caller invokes `exec --base-url <url>`
- **AND** the server reports that no refresh was triggered
- **THEN** the CLI does not perform a compile settle
- **AND** the command does not wait for a compilation that was never started

### Requirement: ExecRequest protocol carries optional import context fields

The exec HTTP request payload SHALL accept four optional fields alongside the existing `request_id`, `code`, and `wait_timeout_ms`:
- `source_path` (string): absolute path of the entry file; populated automatically by the CLI when `--file` is used.
- `import_base_url` (string): import resolution base; populated when `--import-base-url` is provided.
- `reset_jsenv_before_exec` (bool): when true, the server resets the JsEnv before evaluating; populated when `--reset-jsenv-before-exec` is set.
- `stale_module_policy` (string): `auto-reset` or `error`; omission SHALL mean `auto-reset`.

The payload SHALL NOT carry a `refresh_before_exec` field. Refresh is a server-side decision under `import-change-refresh`, reported in the exec response, and is not caller-selectable.

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

#### Scenario: Payload carrying the removed refresh field is rejected

- **WHEN** a direct HTTP client submits an exec payload carrying `refresh_before_exec`
- **THEN** the server rejects the request with a machine-readable failure naming the removed field
- **AND** it does not execute code or refresh

## ADDED Requirements

### Requirement: Automatic refresh is a non-terminal phase of the accepted exec request

When the server reports that it triggered an automatic refresh, the CLI SHALL treat the refresh and the resulting compilation as non-terminal phases of the same accepted exec request. The CLI SHALL NOT present a refresh confirmation as the caller's script result, and SHALL make the continuation path explicit so a caller does not mistake an intermediate phase for completion.

#### Scenario: Automatic refresh runs the script after settling

- **WHEN** the server triggers an automatic refresh and the refresh triggers a compilation
- **THEN** the CLI settles on the compile cycle before running the caller's script
- **AND** the terminal response carries the script result, not a refresh confirmation

#### Scenario: Caller observes an intermediate refreshing or compiling phase

- **WHEN** an exec request is still refreshing or compiling when a response is returned
- **THEN** the response represents a non-terminal accepted state rather than a terminal result
- **AND** the response makes the continuation path explicit so the caller can wait for the eventual script result

### Requirement: Help states that only code changes trigger automatic refresh

The formal CLI help surface SHALL state explicitly that automatic refresh watches code changes only — C# sources, assembly definitions and references, and compiler response files — and that scenes, prefabs, metadata files, textures, audio, and other non-code assets do not trigger it. The statement SHALL appear wherever refresh behavior is described, not only in an option list, so that a caller relying on asset import discovers the boundary without inference. Help SHALL direct callers who need a non-code asset imported to invoke `AssetDatabase.Refresh()` through the bridge.

#### Scenario: Agent reads exec help and learns the code-only boundary

- **WHEN** a caller reads `exec --help`
- **THEN** the help states that refresh is automatic for code changes
- **AND** it names that non-code assets are not watched
- **AND** it names `AssetDatabase.Refresh()` through the bridge as the remedy for a non-code import

#### Scenario: Agent reads compile-error guidance and learns the code-only boundary

- **WHEN** a caller reads guidance that mentions refresh or recompilation
- **THEN** that guidance does not imply that saving a scene or prefab triggers a refresh

### Requirement: Removed --refresh-before-exec reports an actionable usage error

The CLI SHALL retain `--refresh-before-exec` in the `exec` parser solely to produce a machine-readable usage error. Supplying it SHALL raise a usage failure carrying a `situation` that explains the removal and states that refresh is now automatic for code changes. The CLI SHALL NOT treat it as an unrecognized argument, and SHALL NOT honor it as a refresh request.

#### Scenario: Caller supplies the removed flag

- **WHEN** `exec --project-path <path> --refresh-before-exec --file entry.js` is invoked
- **THEN** the command fails as a usage error before contacting the server
- **AND** the payload includes a `situation` explaining that refresh is automatic for code changes
- **AND** the payload does not describe the flag as unrecognized

#### Scenario: Usage failure does not partially apply

- **WHEN** a caller supplies the removed flag alongside otherwise valid arguments
- **THEN** no exec request is submitted and no refresh occurs
