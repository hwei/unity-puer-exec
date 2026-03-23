## Context

Pending exec artifacts currently exist to bridge one specific gap: project-scoped `exec` can now enter an accepted `running` lifecycle before Unity is ready, and `wait-for-exec` can later submit the original request once startup completes.

The current shape is intentionally minimal:

- artifacts are stored under the target Unity project's `Temp/UnityPuerExec/pending_exec/`
- they are keyed by `request_id`
- they persist the original script content long enough for later recovery

This is good enough for the first Prompt A slice, but not yet a fully hardened lifecycle policy.

## Open Questions

- When should pending exec artifacts expire automatically?
- Which terminal outcomes should always delete the artifact immediately?
- How should the CLI distinguish a legitimately recoverable pending exec from a stale leftover record?
- Should any cleanup happen opportunistically during later `exec` / `wait-for-exec` calls, or only when a dedicated retention rule is introduced?

## Intended Outcome

This follow-up should eventually expand into a complete change that:

- defines the pending exec artifact lifecycle explicitly
- adds the necessary cleanup and retention behavior
- proves the behavior with focused tests

Until then, this spike exists only to keep the hygiene concern visible and bounded.
