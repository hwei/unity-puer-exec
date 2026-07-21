## MODIFIED Requirements

### Requirement: Server tracks source file modification times

The C# execution server SHALL maintain a JsEnv-scoped mapping from every local filesystem module successfully read by `PuerExecLoader` to the file existence and `File.GetLastWriteTimeUtc` observed at that read. Paths SHALL be normalized absolute paths. The mapping SHALL include entry files and transitively imported local files, SHALL exclude virtual, HTTP/HTTPS, and resource-backed modules, and SHALL be cleared when the JsEnv is disposed or reset.

#### Scenario: Loader records an entry and transitive local module

- **WHEN** an exec entry file imports a local module and `PuerExecLoader` successfully reads both files
- **THEN** the server records a fingerprint for the normalized absolute path of each file

#### Scenario: Timestamps are cleared on JsEnv reset

- **WHEN** `ResetJsEnv()` is called through an exec-scoped reset or the `/reset-jsenv` endpoint
- **THEN** the entire local module fingerprint mapping is cleared
- **AND** the fresh JsEnv records new fingerprints as it loads modules

#### Scenario: Non-filesystem modules are not tracked

- **WHEN** `PuerExecLoader` reads a virtual, HTTP/HTTPS, or resource-backed module
- **THEN** that module is not added to the local filesystem fingerprint mapping

### Requirement: Server rejects execution when source file has been modified

Before accepting a new exec request, the server SHALL compare the current filesystem state of every tracked local module with its recorded fingerprint. Changed and removed paths SHALL form a sorted, deduplicated stale-module list. If the list is non-empty and the effective stale-module policy is `auto-reset`, the server SHALL reserve the request, reset the JsEnv once on the main thread, and execute the request in the same submission. If the effective policy is `error`, the server SHALL reject the request with `status = "module_cache_stale"` before job creation. In either case, a reset SHALL NOT occur while another exec request is active.

#### Scenario: Modified entry is recovered automatically by default

- **WHEN** an entry file previously loaded by the current JsEnv has a different `File.GetLastWriteTimeUtc`
- **AND** a new exec request omits the stale-module policy
- **THEN** the server treats the effective policy as `auto-reset`
- **AND** the server resets the JsEnv once and executes the request in the same submission

#### Scenario: Modified transitive import is recovered automatically

- **WHEN** an unchanged entry imports a local module previously loaded by the current JsEnv
- **AND** the imported module's `File.GetLastWriteTimeUtc` has changed
- **THEN** the imported module appears in the stale-module list
- **AND** the default policy resets the JsEnv once before executing updated module content

#### Scenario: Removed loaded module is stale

- **WHEN** a local module recorded by the current JsEnv no longer exists
- **THEN** its normalized path appears in the stale-module list
- **AND** recovery or error handling follows the effective policy before downstream module resolution

#### Scenario: Error policy rejects without state mutation

- **WHEN** at least one tracked local module is stale
- **AND** the request selects `stale_module_policy = "error"`
- **THEN** the server returns `{"ok": false, "status": "module_cache_stale"}` with the affected paths
- **AND** no new job is created
- **AND** the JsEnv and existing `activeRequestId` are not affected

#### Scenario: Active exec prevents recovery reset

- **WHEN** a different exec request is active
- **AND** a new request would otherwise require stale-module recovery
- **THEN** the new request receives the normal `busy` outcome
- **AND** the server does not reset the JsEnv

#### Scenario: Unchanged tracked modules proceed without reset

- **WHEN** every tracked local module still exists with its recorded `File.GetLastWriteTimeUtc`
- **THEN** the request proceeds through normal job creation and execution
- **AND** no stale recovery reset occurs

#### Scenario: No tracked local modules proceeds normally

- **WHEN** the current JsEnv has no tracked local filesystem modules
- **THEN** the request proceeds normally regardless of whether its source is file, code, or stdin

### Requirement: CLI surfaces module_cache_stale with actionable guidance

When the CLI receives `module_cache_stale` from an `exec` command using `--stale-module-policy error`, it SHALL include a `situation` explanation, the sorted affected module paths, and `next_steps` candidates. The first candidate SHALL include a concrete argv for explicitly resetting before exec. The guidance SHALL also explain that omitting the error policy enables default same-invocation recovery.

#### Scenario: Agent receives module_cache_stale under error policy

- **WHEN** `unity-puer-exec exec --project-path X:/project --file X:/scripts/stale.js --stale-module-policy error` detects a changed loaded module
- **THEN** the response includes a `situation` string explaining that reset was withheld by policy
- **AND** the response includes the affected local module paths
- **AND** the first `next_steps` candidate carries `--reset-jsenv-before-exec`
- **AND** another candidate explains how to use the default `auto-reset` policy

#### Scenario: wait-for-exec does not newly detect staleness

- **WHEN** `wait-for-exec` is invoked for a previously accepted request
- **THEN** it does not perform a new filesystem staleness check
- **AND** it returns the accepted job's existing result, including recovery metadata when that job performed recovery
