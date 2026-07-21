## 1. Protocol and CLI policy

- [x] 1.1 Add `stale_module_policy` validation/defaulting to the Unity exec protocol and focused package-layout/protocol tests for omitted, valid, and invalid values.
- [x] 1.2 Add `--stale-module-policy auto-reset|error` to CLI parsing and help, then carry the effective value through payload construction and pending-exec persistence/resume with focused CLI/module-state tests.
- [x] 1.3 Remove the CLI's exec-time `/reset-jsenv` pre-call while retaining `reset_jsenv_before_exec` in the submitted payload and the independent reset command; update refresh ordering and single-reset call assertions.

## 2. Loader-backed staleness detection

- [x] 2.1 Replace entry-only timestamp bookkeeping with a synchronized JsEnv-scoped fingerprint map populated after successful local filesystem reads in `PuerExecLoader`, excluding virtual, HTTP/HTTPS, and resource-backed modules.
- [x] 2.2 Implement deterministic stale snapshots for changed and removed tracked paths, clear the complete map on dispose/reset, and add focused tests for entries, transitive imports, exclusions, unchanged files, and deletion.

## 3. Atomic recovery and response evidence

- [x] 3.1 Refactor exec admission so request-id replay/conflict and active-exec checks precede recovery, a new request is reserved before its main-thread reset, and `error` policy rejects without job creation or JsEnv mutation.
- [x] 3.2 Perform at most one server-owned reset for a newly accepted request, with explicit reset taking precedence over policy and refresh still settling before the server receives the request.
- [x] 3.3 Store the reset plan/evidence with the exec job and serialize terminal `recovery` metadata for automatic and explicit reset paths, while returning sorted stale module paths on `module_cache_stale` errors.
- [x] 3.4 Add server and CLI regression tests for default auto recovery, explicit `error`, explicit-reset precedence, active-request `busy`, idempotent replay, synchronous completion, and `exec` running followed by `wait-for-exec`.

## 4. Guidance and validation

- [x] 4.1 Update `exec` help, `--help-status`, situations, and next-step guidance to explain the default behavior, state-loss trade-off, `error` opt-out, affected paths, and explicit reset recovery.
- [x] 4.2 Run the focused repository test suites covering CLI parsing/runtime/pending state, protocol/package layout, and response contracts; record exact commands and results in the apply evidence.
- [x] 4.3 Validate on the configured real Unity host that an entry edit and a transitive-import edit both auto-reset and execute updated content, `error` preserves JsEnv state, a running exec prevents reset, and the observed reset count is exactly one.
- [x] 4.4 Run `openspec validate auto-recover-stale-modules --strict`, review implementation findings under the apply-closeout contract, and leave the change ready for the human-directed commit/archive sequence.
