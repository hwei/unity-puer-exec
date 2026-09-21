## REMOVED Requirements

### Requirement: refresh_before_exec triggers native AssetDatabase.Refresh

**Reason**: Refresh is no longer caller-requested. Under `import-change-refresh` the server decides whether to refresh based on observed compile-triggering changes, so there is no protocol field or early-return refresh path to describe. The condition this requirement supplied to the compile error gate is also gone.

**Migration**: Remove the `refresh_before_exec` field from `ExecRequest`. Refresh now happens automatically when the server detects a code change. Callers needing a non-code asset imported invoke `AssetDatabase.Refresh()` through the bridge.

## MODIFIED Requirements

### Requirement: Exec endpoint returns unity_compile_error when compilation had errors

When the `/exec` endpoint receives a valid execution request, the server SHALL check `_lastCompilationHadErrors` after the `IsCompilingOrReloading()` check and before JavaScript execution. When the flag is true, the server SHALL return `{"ok": false, "status": "unity_compile_error"}` with inline compile diagnostics instead of proceeding to execution. The gate SHALL be evaluated after the automatic refresh decision, so that a code change made to fix a compilation error is recompiled rather than reported as still failing. The gate SHALL NOT be evaluated against a caller-supplied refresh flag, because no such flag exists.

#### Scenario: Exec with compile errors present

- **WHEN** a valid `/exec` request arrives
- **AND** `_lastCompilationHadErrors` is true
- **AND** the server is not currently compiling
- **THEN** the response has `ok: false` and `status: "unity_compile_error"`
- **AND** the response includes `compile_errors_total`, `compile_warnings_total`, and `compile_messages`
- **AND** JavaScript execution is not started

#### Scenario: Exec with no compile errors

- **WHEN** a valid `/exec` request arrives and `_lastCompilationHadErrors` is false
- **THEN** the server proceeds to the existing execution logic

#### Scenario: Compile error gate is checked after request parsing

- **WHEN** a valid `/exec` request arrives
- **THEN** the server parses and validates the request before evaluating the compile error gate
- **AND** the gate is evaluated after the automatic refresh decision and before JavaScript execution

#### Scenario: Compile error gate yields to an automatic refresh

- **WHEN** a valid `/exec` request arrives while `_lastCompilationHadErrors` is true
- **AND** the server detects a pending compile-triggering change
- **THEN** the server performs the automatic refresh first so the change can be recompiled
- **AND** the compile error gate is evaluated against the refreshed compilation result, not the pre-refresh one

#### Scenario: Compile error gate applies when no change is pending

- **WHEN** a valid `/exec` request arrives while `_lastCompilationHadErrors` is true
- **AND** the server detects no pending compile-triggering change
- **THEN** the server returns `unity_compile_error` without refreshing
- **AND** JavaScript execution is not started
