## Context

The current server records only `ExecRequest.source_path`, rejects a changed entry before job creation, and tells the caller to resubmit with `--reset-jsenv-before-exec`. `PuerExecLoader.ReadFile` is the actual authority that sees every local module loaded into the long-lived JsEnv, but it does not retain those paths. As a result, changing a transitively imported file can leave cached code in use without a stale signal.

Explicit reset also has two execution paths today: the CLI calls `/reset-jsenv` before submission and still sends `reset_jsenv_before_exec=true`, after which the server resets again before evaluation. The inherited findings remain that JsEnv reset is the correct cache invalidation mechanism and refresh must settle before reset; this change addresses detection coverage, automatic recovery, concurrency, and the duplicated reset authority.

These are durable product behaviors, so they belong in the affected specs rather than repository-wide `config.yaml` context. Validation-host setup and evidence remain in the integration workflow and do not become product contract.

## Goals / Non-Goals

**Goals:**

- Detect changes and removals for every local filesystem module actually read by `PuerExecLoader`, including transitive imports.
- Make same-invocation auto-reset the default while preserving an explicit fail-fast policy.
- Expose every exec-scoped reset with deterministic machine-readable recovery details.
- Guarantee that recovery never resets the JsEnv underneath another active exec and that each exec request has one reset authority.
- Preserve refresh-before-reset ordering, request idempotency, pending-exec replay, and the standalone reset endpoint.

**Non-Goals:**

- Hot-reload individual ES modules without recreating the JsEnv.
- Detect changes to HTTP modules, virtual harness modules, `Resources` assets, or arbitrary state in `ctx.globals`.
- Preserve the previous fail-fast behavior as the default.
- Add content hashing or filesystem watching; the existing `LastWriteTimeUtc` basis remains.
- Automatically snapshot or restore JS globals and module singleton state across reset.

## Decisions

### The Unity server owns exec-scoped reset

The CLI will no longer call `/reset-jsenv` as a pre-step for `exec`. It will send `reset_jsenv_before_exec` and `stale_module_policy` in the exec payload, and the Unity server will perform at most one reset for a newly accepted request on the main thread immediately before evaluation. The standalone endpoint remains available for independent reset commands.

This keeps stale detection, active-request admission, reset, and execution in one process and closes the race between a CLI pre-reset and server admission. Keeping the CLI pre-reset instead was rejected because auto recovery originates from server-only loader state and cannot be made atomic across two HTTP calls.

### Loader reads populate a JsEnv-scoped module fingerprint map

After `PuerExecLoader.ReadFile` successfully resolves a local filesystem file, it will normalize the absolute path and record an existence/`LastWriteTimeUtc` fingerprint in a server-owned map associated with the current JsEnv. Virtual, HTTP, and resource-backed modules are excluded. The map is cleared whenever the JsEnv is disposed.

Before admission, the server compares every tracked local module with its current filesystem state. Changed and removed files become a sorted, deduplicated affected-module list. Recording at the loader boundary is preferred over parsing import syntax or walking from `source_path`, because the loader observes the actual transitive resolution result.

### Admission reserves the request before scheduling a recovery reset

Under the existing request gate, the server will first preserve request-id replay/conflict behavior, reject a genuinely different running request as `busy`, evaluate the tracked-module snapshot, and reserve a new request. The main-thread action then performs any planned reset and starts evaluation. Because the request is already the active reservation, no second exec can be admitted between the stale decision and reset.

An idempotent replay of the same `request_id` returns the existing job/result and does not repeat reset. Staleness with policy `error` is rejected without creating a job. This ordering is preferred over resetting before request admission, which could destroy state even though another exec should have caused a `busy` response.

### Policy and explicit reset have deterministic precedence

`stale_module_policy` accepts `auto-reset` and `error`; omission means `auto-reset` on both CLI and server. If tracked modules are stale and policy is `auto-reset`, the accepted request plans one reset. Under `error`, the server returns `module_cache_stale` with the affected paths and does not reset or create a job.

`reset_jsenv_before_exec=true` always plans one reset regardless of policy. It therefore remains the explicit escape hatch and preserves refresh-then-reset semantics. When both explicit reset and stale modules are present, the recovery reason is `explicit_request` and the affected paths are still reported.

### Recovery metadata is attached to the terminal exec response

When an exec-scoped reset occurs, the response includes a `recovery` object with `performed=true`, `type="jsenv_reset"`, `reason` (`module_cache_stale` or `explicit_request`), `policy`, and a sorted `affected_modules` array. Responses without a reset omit `recovery`. An `error`-policy stale response includes `stale_modules` but no successful recovery claim.

The recovery plan is stored with the job so synchronous completion and later `wait-for-exec` retrieval expose the same metadata. This is preferred over CLI-only decoration, which would lose the evidence on the running/wait path and for direct HTTP clients.

### Pending exec state preserves the policy

The CLI persists the effective policy alongside other pending exec inputs. Resubmission after startup, refresh, or compilation uses the same value. CLI help explains that callers relying on `ctx.globals` or module singleton continuity should select `error` and decide when to reset explicitly.

## Risks / Trade-offs

- [Risk] Default auto-reset can discard caller-owned JS globals or singleton state. → Mitigation: document the behavior, report recovery explicitly, and provide `--stale-module-policy error`.
- [Risk] Timestamp-only detection can miss edits that preserve filesystem mtime. → Mitigation: retain the established contract for this change and leave hashing/watchers as separate follow-up work.
- [Risk] Tracking all loaded local modules can reset for a changed module unrelated to the next entry. → Mitigation: treat the JsEnv module cache as the safety boundary; a global reset is conservative and matches the actual cache scope.
- [Risk] Recording fingerprints from loader callbacks and checking them on the listener path can introduce synchronization bugs. → Mitigation: guard snapshot/map mutation explicitly and validate concurrent busy/replay paths.
- [Risk] Response shape changes can expose path information. → Mitigation: report only local paths already loaded by caller-submitted code and do not include file contents.

## Migration Plan

1. Add protocol and job-state fields with server-side omission defaulting to `auto-reset`.
2. Move explicit exec reset authority fully into the server and update CLI/pending-state wiring.
3. Replace entry-only timestamps with loader-populated local-module fingerprints and add recovery response serialization.
4. Update help, unit/integration tests, and real-host regression coverage before archive.
5. Roll back by selecting `--stale-module-policy error`; a code rollback restores the prior default without migrating persisted product data.

## Open Questions

None. Content hashing and automatic temporary-file policies are intentionally outside this change.
