## ADDED Requirements

### Requirement: Server tracks source file modification times

The C# execution server SHALL maintain a mapping from absolute `source_path` to the `File.GetLastWriteTimeUtc` observed when a `--file` exec request was last accepted for execution. The mapping SHALL be cleared when the JsEnv is disposed or reset.

#### Scenario: First execution of a file records its mtime

- **WHEN** an exec request with `source_path` is first accepted and executed
- **THEN** the server records `File.GetLastWriteTimeUtc` for that path at the time of job start

#### Scenario: Timestamps are cleared on JsEnv reset

- **WHEN** `ResetJsEnv()` is called (via `--reset-jsenv-before-exec` or the `/reset-jsenv` endpoint)
- **THEN** the entire source file timestamp mapping is cleared
- **AND** the next execution of any previously-tracked file proceeds without staleness rejection

### Requirement: Server rejects execution when source file has been modified

Before accepting a new exec request that carries a `source_path`, the server SHALL compare the current `File.GetLastWriteTimeUtc` against the stored timestamp for that path. If the path has been previously executed and the current mtime differs from the stored value, the server SHALL reject the request with `status = "module_cache_stale"` before creating a job or checking idempotency.

#### Scenario: Modified file is rejected before execution

- **WHEN** `exec --file /scripts/analyze.js` is invoked
- **AND** `/scripts/analyze.js` was previously executed and its `File.GetLastWriteTimeUtc` has changed
- **THEN** the server returns `{"ok": false, "status": "module_cache_stale"}`
- **AND** no new job is created
- **AND** the existing `activeRequestId` is not affected

#### Scenario: Unchanged file proceeds normally

- **WHEN** `exec --file /scripts/analyze.js` is invoked
- **AND** `/scripts/analyze.js` was previously executed but its `File.GetLastWriteTimeUtc` has not changed
- **THEN** the request proceeds through normal job creation and execution

#### Scenario: New file with no prior execution proceeds normally

- **WHEN** `exec --file /scripts/new-script.js` is invoked
- **AND** `/scripts/new-script.js` has no entry in the timestamp mapping
- **THEN** the request proceeds through normal job creation and execution
- **AND** the file's mtime is recorded

#### Scenario: Missing file is treated as not stale

- **WHEN** `exec --file /scripts/deleted.js` is invoked
- **AND** the file does not exist on disk (or was deleted since the last recorded timestamp)
- **THEN** the server treats the staleness check as passed (no cached module to worry about)
- **AND** the normal file-not-found or execution error surfaces from downstream processing

#### Scenario: Code mode is never stale

- **WHEN** an exec request does not carry a `source_path` (e.g., `--code` or `--stdin` mode)
- **THEN** the staleness check is skipped entirely
- **AND** the request proceeds normally

### Requirement: CLI surfaces module_cache_stale with actionable guidance

When the CLI receives a `module_cache_stale` response from an `exec` command, it SHALL include a `situation` explanation and `next_steps` candidates. The first candidate SHALL include a concrete `argv` for re-running with `--reset-jsenv-before-exec`. An additional candidate SHALL suggest renaming the source file to bypass the cache.

#### Scenario: Agent receives module_cache_stale on exec

- **WHEN** `unity-puer-exec exec --project-path X:/project --file X:/scripts/stale.js` returns `status = "module_cache_stale"`
- **THEN** the response includes a `situation` string explaining that the file changed but the module cache is stale
- **AND** the response includes `next_steps` with at least two candidates
- **AND** the first candidate has `command = "exec"` with `argv` including `--reset-jsenv-before-exec`
- **AND** an additional candidate suggests renaming the file

#### Scenario: wait-for-exec does not produce module_cache_stale

- **WHEN** `wait-for-exec` is invoked for a previously-accepted request
- **THEN** staleness checking is not performed (it was already checked at `exec` submission time)
- **AND** `module_cache_stale` is never a status for `wait-for-exec` responses
