## Why

File-backed exec currently rejects a stale module cache and requires the caller to resubmit manually, while only the entry file's modification time is checked. This leaves a routine recovery step to agents, permits changed local dependencies to execute from stale cache without warning, and currently allows a requested reset to be performed by both the CLI and Unity server.

## What Changes

- Add `--stale-module-policy auto-reset|error`, defaulting to `auto-reset`, so a stale local module graph can be reset and executed within the same CLI invocation while state-sensitive callers can retain fail-fast behavior.
- Include machine-readable `recovery` details in a successfully recovered exec response, including the reset reason and affected local module paths.
- Track all local filesystem modules read by `PuerExecLoader`, including transitive imports, and detect changed or removed tracked modules before accepting a later exec.
- Make stale recovery concurrency-safe: perform reset only after confirming there is no other active exec, and keep a single authoritative reset execution point.
- Eliminate the current CLI-plus-server double reset while preserving explicit `--reset-jsenv-before-exec` and the standalone `/reset-jsenv` endpoint.
- Replace the existing default contract that returns `module_cache_stale` and asks callers to resubmit; that status remains available under `stale-module-policy=error`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cache-staleness-detection`: Expand staleness tracking from entry files to every local filesystem module loaded into the JsEnv, and define concurrency-safe automatic reset behavior.
- `exec-import-support`: Change the stale-module remedy from mandatory caller resubmission to policy-controlled same-invocation recovery and establish one authoritative reset point.
- `formal-cli-contract`: Add the stale-module policy option and machine-readable recovery response contract while retaining an explicit error policy.

## Impact

- CLI argument parsing, help/status guidance, pending-exec persistence, request payload construction, and response normalization under `cli/python/`.
- Unity request protocol, exec admission/reset sequencing, loader module tracking, staleness bookkeeping, and response serialization in `packages/com.txcombo.unity-puer-exec/Editor/`.
- Repository-level CLI/protocol tests plus real validation-host coverage for entry and transitive dependency changes, policy override, recovery metadata, active-exec exclusion, and single-reset behavior.
- Existing callers that rely on `module_cache_stale` as the default outcome must opt into `--stale-module-policy error`; this is an intentional default behavior change.
