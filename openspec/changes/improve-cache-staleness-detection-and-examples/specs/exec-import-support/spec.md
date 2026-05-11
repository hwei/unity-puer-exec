## ADDED Requirements

### Requirement: Staleness detection is the entry-point guard; reset is the remedy

The mtime-based staleness detection (see `cache-staleness-detection`) SHALL act as the entry-point guard that alerts users when `--reset-jsenv-before-exec` is needed. When staleness is detected, the server SHALL reject the request before job creation. The user SHALL then re-submit with `--reset-jsenv-before-exec` to clear the module cache and proceed.

#### Scenario: Staleness detection prompts the user to use reset

- **WHEN** `exec --file entry.js` returns `module_cache_stale`
- **THEN** the CLI guidance directs the user to re-run with `--reset-jsenv-before-exec`
- **AND** re-running with `--reset-jsenv-before-exec` clears both the JsEnv module cache and the mtime tracking state
- **AND** the updated file content is loaded
