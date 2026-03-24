## Context

The archived spike `harden-pending-exec-artifact-lifecycle` established the baseline for this follow-up:

- project-scoped `exec` now persists a pending artifact under the target Unity project's `Temp/UnityPuerExec/pending_exec/` directory so accepted work can continue through `wait-for-exec`
- the current artifact is intentionally minimal and only stores enough information to replay the original request later
- cleanup is currently branch-local and incomplete, and malformed or expired local leftovers do not have a durable lifecycle contract yet

The gap is no longer about whether pending artifacts are needed. That upstream finding remains true. The gap is that the repository still lacks a durable contract for how long those artifacts live, which metadata they carry, how stale or malformed files are treated, and when cleanup happens.

This design belongs in change-local `design.md` because it chooses one implementation shape for this change. The durable caller-facing requirements belong in `openspec/specs/`, not in `openspec/project.md`, because retention-driven recovery behavior and validation expectations are product and verification contracts rather than repository-only workflow guidance.

## Goals / Non-Goals

**Goals:**

- Define one bounded local retention contract for pending exec artifacts.
- Preserve the accepted `exec -> running -> wait-for-exec` recovery path for realistic startup and compile delays.
- Centralize lifecycle cleanup so terminal, expired, and malformed artifact handling is consistent.
- Keep caller-visible machine states simple by continuing to fold stale local leftovers into `missing`.
- Add unit and host-validation coverage for the hardened lifecycle.

**Non-Goals:**

- Introduce cross-session resurrection beyond the existing request lifecycle.
- Replace stored script bodies with a different replay-token architecture.
- Add a new public status such as `stale_local_artifact` in this change.
- Turn retention tuning into a user-facing CLI option.

## Decisions

### Decision: Use a versioned artifact schema with explicit timestamps

Pending artifact JSON will carry a small explicit schema:

- `schema_version`
- `request_id`
- `code`
- `refresh_before_exec`
- optional transient lifecycle fields such as `phase` and `refresh_request_id`
- `created_at_ms`
- `updated_at_ms`

Epoch-millisecond timestamps keep comparison logic simple in Python and deterministic in tests. `schema_version` gives the reader a stable way to treat malformed or obsolete files as non-recoverable local leftovers instead of trying to infer compatibility from missing fields.

Alternatives considered:

- ISO-8601 timestamp strings. Rejected because parsing and comparison are noisier in the current Python helpers without adding real caller value.
- Keep implicit timestamps from filesystem metadata. Rejected because the retention contract would then depend on platform-specific file behavior instead of explicit persisted state.

### Decision: Adopt a fixed 24-hour retention window for local pending artifacts

Pending artifacts will remain recoverable for up to 24 hours from their latest update. Every recoverable transition that still represents the same accepted request will refresh `updated_at_ms`.

This window is long enough for realistic agent interruptions, Unity import delays, and operator handoff, while still bounding Temp-directory buildup and script-body persistence. The value should live as a repository constant in the CLI helper layer rather than as a new public flag.

Alternatives considered:

- A much shorter window such as minutes. Rejected because it risks invalidating legitimate same-day recovery flows after editor startup, compilation, or human review pauses.
- An unbounded window. Rejected because it leaves stale script bodies in Temp indefinitely and keeps the current hygiene problem unsolved.
- A user-configurable retention flag. Rejected because the contract should stay simple until there is a demonstrated product need for caller-controlled policy.

### Decision: Keep stale or malformed local records folded into `missing`

If `wait-for-exec` targets a pending artifact that is expired, malformed, or uses an unsupported schema, the CLI will delete that local file opportunistically and return the same machine-readable `missing` result used for other non-recoverable request lookups.

This keeps the public recovery surface stable and matches the existing durable CLI contract that `missing` does not distinguish never-seen, lost-with-session-replacement, or aged-out retention outcomes. The hardening value of this change is better local cleanup and durability, not a broader external status taxonomy.

Alternatives considered:

- Add a distinct external status for stale local leftovers. Rejected because it would expand the public state space without first proving that callers materially benefit from the distinction.
- Continue silently ignoring malformed files without cleanup. Rejected because it preserves Temp-directory buildup and hides local corruption behind repeated re-reads.

### Decision: Opportunistically sweep the whole pending directory, but only delete clearly stale siblings

Project-scoped `exec` and `wait-for-exec` will perform best-effort cleanup of the pending artifact directory for the addressed project. The sweep will:

- delete malformed or unsupported-schema files
- delete expired files
- leave non-expired unrelated siblings untouched

Using a directory sweep instead of only touching the addressed request prevents stale buildup from accumulating when callers naturally continue using the same project. Restricting deletion to clearly stale siblings avoids violating the single-request continuity contract for still-recoverable work.

Alternatives considered:

- Only inspect the addressed request id. Rejected because abandoned siblings would continue accumulating until manual cleanup.
- Delete every sibling except the addressed request. Rejected because that could destroy still-valid recoverable work after crashes or overlapping investigative flows.

### Decision: Centralize terminal cleanup in lifecycle helpers

The implementation will move pending artifact deletion and refresh decisions behind shared helper functions rather than letting each runtime branch decide ad hoc. The helpers will expose a small lifecycle vocabulary: write-or-refresh recoverable state, load-and-validate target state, opportunistic sweep, and finalize terminal outcome.

This reduces the current risk that one failure branch forgets to delete a file while another branch handles the same outcome differently.

Alternatives considered:

- Preserve branch-local delete calls and patch only the known gaps. Rejected because the spike already showed that scattered cleanup is the underlying reason the lifecycle is inconsistent.

## Risks / Trade-offs

- [A 24-hour window may still be too long for sensitive script persistence] → Mitigation: keep the value centralized, document it explicitly, and revisit only if validation or security review shows real pressure.
- [Directory sweeps could add minor latency to project-scoped commands] → Mitigation: the pending directory is expected to stay small, and the sweep work is bounded to cheap JSON validation plus deletion of clearly stale files.
- [Folding expired or malformed records into `missing` may hide useful diagnostics from advanced callers] → Mitigation: keep internal logging and tests precise even though the public machine state remains simple.
- [Centralizing lifecycle logic may touch several Python modules at once] → Mitigation: keep the helper boundary narrow and back it with targeted unit tests before host validation.

## Migration Plan

1. Extend the pending artifact helper schema and reader/writer behavior.
2. Route project-scoped `exec` and `wait-for-exec` through the centralized lifecycle helpers.
3. Update unit tests to cover fresh, expired, malformed, and terminal-cleanup paths.
4. Run the targeted real-host validation pass to confirm the normal accepted lifecycle still works.
5. If regressions appear, revert to the previous helper behavior in code while keeping the change artifacts for the next iteration.

## Open Questions

- Whether the implementation should expose an internal debug trace when malformed sibling cleanup occurs, even though the public status remains `missing`.
- Whether future work should shrink or eliminate persisted script bodies after this lifecycle change proves stable.
