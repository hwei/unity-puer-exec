# Spec Delta

## MODIFIED Requirements

### Requirement: Staleness detection is the entry-point guard; reset is the remedy

The mtime-based staleness detection defined by `cache-staleness-detection` SHALL guard reuse of
every local filesystem module loaded by the current JsEnv. The default remedy SHALL be a single
server-owned JsEnv reset followed by execution in the same CLI invocation. A caller that
requires `ctx.globals` or module singleton continuity SHALL be able to select
`stale-module-policy=error`, in which case the server SHALL reject the request before job
creation and require an explicit reset decision.

The guard SHALL apply to caller-owned modules only. A filesystem `--import-base-url` SHALL NOT
itself cause a staleness reset: the server's own per-request entry module is excluded from the
tracked set, so `ctx.globals`, module singletons, and other JsEnv-scoped state SHALL survive
across successive execs that use that mode, and `stale-module-policy=error` SHALL NOT reject
them for a change the server caused.

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

#### Scenario: A filesystem import base URL preserves JsEnv continuity

- **WHEN** two successive execs both use the same filesystem `--import-base-url`
- **AND** neither the caller's entry code nor any imported module changed on disk
- **THEN** the second exec reports no staleness recovery
- **AND** state the first exec stored on `ctx.globals` is still visible to the second

#### Scenario: A changed caller module in the base directory is still stale

- **WHEN** an exec uses a filesystem `--import-base-url`
- **AND** a caller-owned module that the previous exec imported is modified on disk
- **THEN** that module appears in the stale-module list
- **AND** recovery or rejection follows the effective stale-module policy
