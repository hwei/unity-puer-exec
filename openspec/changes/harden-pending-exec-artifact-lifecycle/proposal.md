## Why

The first Prompt A continuity slice introduced a project-local pending exec artifact under the Unity host project's `Temp/UnityPuerExec/pending_exec/` area so `exec --project-path ...` can return an accepted `running` lifecycle before Unity startup is fully ready.

That behavior is acceptable for the current product step, but the artifact lifecycle is still intentionally loose. Interrupted runs can leave stale files behind, and the current implementation does not yet define stronger retention, expiry, or stale-record cleanup rules.

## What Changes

- Record a follow-up investigation for tightening pending exec artifact lifecycle behavior.
- Keep the current Prompt A continuity implementation unchanged until this narrower hygiene question is explored separately.
- Prepare a future implementation-oriented change that can define retention, cleanup, and stale-record handling without silently expanding the current verification-closure work.

## Impact

- Tracks a bounded follow-up about temporary artifact hygiene in the Unity host project.
- Depends on `improve-agent-verification-closure`, because that change introduced the pending exec artifact behavior.
