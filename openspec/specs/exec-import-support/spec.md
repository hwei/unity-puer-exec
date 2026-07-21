# Exec Import Support

## Purpose

Define the durable contract for ES module import support in `unity-puer-exec`, including import resolution behavior for file, code, and stdin execution paths and the JsEnv reset workflow used to clear the module cache.
## Requirements
### Requirement: Exec entry scripts may use static ES module imports
The exec execution model SHALL support ES module context. Entry scripts MAY contain static `import` declarations. The runtime SHALL resolve imported modules according to the entry specifier and the active base URL. Scripts without `import` statements SHALL continue to execute unchanged.

#### Scenario: Entry script imports a local sibling module
- **WHEN** `exec --file entry.js` is invoked and `entry.js` contains `import { x } from './lib.js'`
- **THEN** the runtime resolves `./lib.js` relative to the directory containing `entry.js`
- **AND** the execution succeeds if `lib.js` exists at that path

#### Scenario: Entry script uses a default export alongside imports
- **WHEN** an entry script contains both static `import` declarations and `export default function(ctx) { ... }`
- **THEN** the runtime accepts the script and passes `ctx` to the default-exported function
- **AND** imported bindings are available inside the entry function body

### Requirement: --file mode resolves imports relative to the source file
When `exec --file <path>` is used, the runtime SHALL derive the import base from the absolute directory of the source file. Relative imports in the entry and in any transitively imported module SHALL resolve from that file's directory without any additional CLI argument.

#### Scenario: Nested relative import chain resolves correctly
- **WHEN** `exec --file /scripts/main.js` is invoked
- **AND** `main.js` imports `./utils/a.js` which imports `./b.js`
- **THEN** `./utils/a.js` resolves to `/scripts/utils/a.js`
- **AND** `./b.js` inside `a.js` resolves to `/scripts/utils/b.js`

### Requirement: --import-base-url sets the import resolution base for non-file input
When `exec --code` or `exec --stdin` is used, the CLI SHALL accept `--import-base-url <value>`. The value SHALL be either a filesystem directory path or an HTTP/HTTPS URL prefix. The runtime SHALL use this value as the anchor for resolving relative imports from the entry code.

#### Scenario: Filesystem base URL resolves relative imports
- **WHEN** `exec --code "import {x} from './lib.js'; ..." --import-base-url /my/scripts` is invoked
- **THEN** `./lib.js` resolves to `/my/scripts/lib.js` on the filesystem

#### Scenario: HTTP base URL resolves relative imports via synchronous fetch
- **WHEN** `exec --code "import {x} from './lib.js'; ..." --import-base-url http://localhost:3000` is invoked
- **THEN** `./lib.js` is fetched synchronously from `http://localhost:3000/lib.js`
- **AND** execution proceeds with the fetched module content

#### Scenario: --import-base-url is also accepted with --file
- **WHEN** `exec --file entry.js --import-base-url http://localhost:3000` is invoked
- **THEN** the explicit base URL overrides the file-directory default for import resolution

### Requirement: Import without base URL in non-file mode is an explicit error
When `exec --code` or `exec --stdin` is used and the submitted code contains an `import` declaration but `--import-base-url` is not provided, the runtime SHALL return a machine-readable error rather than attempting resolution from an undefined base.

#### Scenario: Code with import lacks base URL
- **WHEN** `exec --code "import {x} from './lib.js'; ..."` is invoked without `--import-base-url`
- **THEN** the command returns a failed result with `error = "missing_import_base_url"`
- **AND** the exit code signals a failure state

### Requirement: HTTP module resolution uses synchronous blocking fetch
The custom ILoader SHALL fetch HTTP and HTTPS module URLs synchronously on the Unity main thread using a blocking HTTP client. This allows the standard PuerTS module resolution flow to remain synchronous.

#### Scenario: Imported HTTP module is fetched before execution begins
- **WHEN** an entry script statically imports a module at an HTTP URL
- **THEN** the ILoader fetches that URL before the entry function is invoked
- **AND** if the fetch fails, exec returns a failed result with a descriptive error

### Requirement: ILoader resolves virtual harness and entry specifiers from memory
The runtime SHALL maintain an in-memory map of per-request virtual modules. The `puer-exec://harness/<requestId>` specifier SHALL return the generated bridge harness. When the entry code is a string under an HTTP base URL, a matching virtual HTTP entry URL SHALL return the code string without performing a real network request.

#### Scenario: Harness module is resolved without disk I/O
- **WHEN** `ExecuteModule("puer-exec://harness/<id>")` is called
- **THEN** the ILoader returns the generated harness content from memory
- **AND** no file is written to disk for the harness

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

### Requirement: A standalone reset-jsenv endpoint exists on the Unity server
The Unity-side HTTP server SHALL expose a `/reset-jsenv` endpoint. Calling it SHALL dispose the current JsEnv and create a new one. This endpoint is used internally by `--reset-jsenv-before-exec` and may also be invoked independently.

#### Scenario: Reset endpoint disposes and recreates JsEnv
- **WHEN** a POST request is made to `/reset-jsenv`
- **THEN** the current JsEnv singleton is disposed
- **AND** a new JsEnv is created with a fresh ILoader instance
- **AND** the response reports `status = "completed"`

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

