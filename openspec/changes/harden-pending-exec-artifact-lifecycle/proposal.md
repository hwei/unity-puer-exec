## Why

The first Prompt A continuity slice introduced a project-local pending exec artifact under the Unity host project's `Temp/UnityPuerExec/pending_exec/` area so `exec --project-path ...` can return an accepted `running` lifecycle before Unity startup is fully ready.

That behavior is acceptable for the current product step, but the artifact lifecycle is still intentionally loose. Interrupted runs can leave stale files behind, and the current implementation does not yet define stronger retention, expiry, or stale-record cleanup rules.

## What Changes

- Confirm the exact current pending exec artifact behavior in code and tests so future cleanup work starts from observed facts rather than assumptions.
- Keep the current Prompt A continuity implementation unchanged in this spike, because the remaining work is no longer just a local code cleanup; it needs an explicit caller-facing lifecycle contract.
- Prepare a future implementation-oriented follow-up that defines retention, cleanup, stale-record handling, and validation coverage without silently expanding the earlier verification-closure work.

## Impact

- Tracks a bounded follow-up about temporary artifact hygiene in the Unity host project.
- Depends on `improve-agent-verification-closure`, because that change introduced the pending exec artifact behavior.
- Establishes that the next step should be a focused implementation change rather than ad hoc cleanup folded into unrelated work.
