## MODIFIED Requirements

### Requirement: --reset-jsenv-before-exec clears the JS module cache
The CLI SHALL accept `--reset-jsenv-before-exec` on the `exec` command. When set, the CLI SHALL express the reset intent in the exec request and the Unity server SHALL dispose the current JsEnv singleton and initialize a fresh one exactly once before executing the script. The CLI SHALL NOT separately invoke `/reset-jsenv` for the same exec. This clears PuerTS's module cache so updated JS library files are reloaded. When the server has also triggered an automatic refresh for pending code changes, the reset SHALL occur after that refresh's compilation settles.

#### Scenario: Module cache is cleared once before exec
- **WHEN** `exec --reset-jsenv-before-exec --file entry.js` is invoked after a JS library file has changed
- **THEN** the server disposes and recreates the JsEnv exactly once before the script runs
- **AND** the updated library file content is loaded during execution
- **AND** the CLI does not issue a separate reset endpoint call

#### Scenario: Ordering when combined with --refresh-before-exec
- **WHEN** an exec request carrying `reset_jsenv_before_exec = true` arrives
- **AND** the server triggers an automatic refresh for pending compile-triggering changes
- **THEN** the refresh step runs first and waits for any compilation to complete
- **AND** the server-owned JsEnv reset runs after compilation, ensuring the fresh JsEnv is not immediately discarded by a compile-triggered reload

#### Scenario: Explicit reset does not occur during another active exec
- **WHEN** an exec request carrying `reset_jsenv_before_exec = true` arrives while a different exec is active
- **THEN** the server returns the normal busy outcome
- **AND** it does not reset the JsEnv
