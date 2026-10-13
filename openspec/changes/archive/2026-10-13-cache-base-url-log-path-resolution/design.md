## Context

`_resolve_base_url_log_path(args)` calls `unity_session.get_log_source(base_url=args.base_url)`,
which probes `/health`. Base-url observation commands call `_resolve_log_path(args, session)` at
more than one point (for example `wait-for-exec` resolves an early path and a final path), and the
base-url bridge guard already probes `/health` once per invocation. Each resolution re-probes even
though the answer cannot change within the invocation.

## Goals / Non-Goals

**Goals:**

- One `/health` probe per invocation for log-path resolution, reused across `_resolve_log_path`
  calls.
- Identical selected path, fallback behavior, and error behavior.

**Non-Goals:**

- Reusing the bridge guard's payload. That couples the version guard to log resolution; caching the
  resolved path keeps the two concerns separate.
- Caching across invocations.

## Decisions

### Decision 1: Cache per invocation on the argument namespace

The resolved path (including a resolved `None`) is memoized on the per-invocation `args`
namespace. `args` is created fresh by the parser for each `run_cli` call, so the cache lifetime
matches the invocation and cannot leak between calls.

### Decision 2: Do not use a process-wide cache

A module-level cache keyed by `base_url` would persist across `run_cli` calls in the same process
and return a stale path when a later invocation targets a different log (notably in the test
suite, which calls `run_cli` repeatedly in one process). The per-invocation namespace avoids that
class of bug entirely.

## Risks / Trade-offs

**[Mutating the argument namespace]** → The cache key is a private, clearly-named attribute; every
read goes through one helper, so no other code depends on it.

**[A resolved path could in principle change mid-invocation]** → The endpoint's reported console
log path does not change while a single command runs, and the base-url `log_range` contract
already assumes a stable file for the duration of the observation.
