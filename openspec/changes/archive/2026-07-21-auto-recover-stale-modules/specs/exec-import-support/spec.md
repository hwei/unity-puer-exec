## MODIFIED Requirements

### Requirement: --reset-jsenv-before-exec clears the JS module cache
The CLI SHALL accept `--reset-jsenv-before-exec` on the `exec` command. When set, the CLI SHALL express the reset intent in the exec request and the Unity server SHALL dispose the current JsEnv singleton and initialize a fresh one exactly once before executing the script. The CLI SHALL NOT separately invoke `/reset-jsenv` for the same exec. This clears PuerTS's module cache so updated JS library files are reloaded.

#### Scenario: Module cache is cleared once before exec
- **WHEN** `exec --reset-jsenv-before-exec --file entry.js` is invoked after a JS library file has changed
- **THEN** the server disposes and recreates the JsEnv exactly once before the script runs
- **AND** the updated library file content is loaded during execution
- **AND** the CLI does not issue a separate reset endpoint call

#### Scenario: Ordering when combined with --refresh-before-exec
- **WHEN** both `--refresh-before-exec` and `--reset-jsenv-before-exec` are provided
- **THEN** the refresh step runs first and waits for any compilation to complete
- **AND** the server-owned JsEnv reset runs after compilation, ensuring the fresh JsEnv is not immediately discarded by a compile-triggered reload

#### Scenario: Explicit reset does not occur during another active exec
- **WHEN** an exec request carrying `reset_jsenv_before_exec = true` arrives while a different exec is active
- **THEN** the server returns the normal busy outcome
- **AND** it does not reset the JsEnv

### Requirement: Staleness detection is the entry-point guard; reset is the remedy

The mtime-based staleness detection defined by `cache-staleness-detection` SHALL guard reuse of every local filesystem module loaded by the current JsEnv. The default remedy SHALL be a single server-owned JsEnv reset followed by execution in the same CLI invocation. A caller that requires `ctx.globals` or module singleton continuity SHALL be able to select `stale-module-policy=error`, in which case the server SHALL reject the request before job creation and require an explicit reset decision.

#### Scenario: Default staleness recovery needs no resubmission

- **WHEN** `exec --file entry.js` detects one or more stale local modules under the default policy
- **THEN** the same CLI invocation resets the JsEnv and executes the entry
- **AND** the final response reports the reset reason and affected modules

#### Scenario: Error policy retains caller control

- **WHEN** `exec --file entry.js --stale-module-policy error` detects one or more stale local modules
- **THEN** the server returns `module_cache_stale` without resetting the JsEnv or creating a job
- **AND** the CLI directs the caller to make an explicit reset or policy choice

#### Scenario: Explicit reset overrides error policy

- **WHEN** `--reset-jsenv-before-exec` and `--stale-module-policy error` are both provided
- **THEN** the explicit reset request causes exactly one server-owned reset before execution
- **AND** the exec is not rejected merely because tracked modules were stale
