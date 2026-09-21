## Context

The failure is deterministic on the validation host and was isolated while applying
`reuse-real-host-editor-across-suite`; it reproduces on both the old per-case-relaunch
harness and the new shared-host harness, so it is pre-existing and independent of that
change. The trigger is the interaction between two shipped behaviors:

1. The import-change tracker notices a compile-triggering write and the CLI's automatic
   refresh settles the resulting compile from the caller's `exec`.
2. The compile completes with a domain reload, which tears down the Editor's script
   environment and the in-process request bookkeeping it held.

Observed sequence (base-url mode, first case after a cold launch):

```
exec (non-terminal accept, request_id R)
  server: triggered=true reason=compile_triggering_change
  -> CLI settles the compile cycle (_settle_base_url_after_refresh)
  -> domain reload
wait-for-exec --request-id R
  -> exit 13, status=missing, "no recoverable record exists for request_id"
     log_range={start:1690261,end:1690261}
```

The `log_range.start` is a large, fixed-looking offset that recurs across runs and full
launches. That is the strongest lead: it looks like an offset captured before a log
rotation/reload and replayed after it, which is exactly the "invalidated log source"
condition `how-to-run.md` already documents for a different failure. If the pending
artifact stores a pre-reload offset and the post-reload record cannot resolve it, then the
`missing` classification is *correct for the artifact as written*, and the defect is that
the CLI caused the reload without carrying the request across it.

## Goals / Non-Goals

**Goals:**

- Identify the single owning call site for the loss of recoverability across the refresh
  domain reload, with evidence, not inference.
- Restore the contract that the terminal response carries the script result.
- Keep genuinely expired or malformed artifacts non-recoverable `missing` (do not silence
  the status wholesale).

**Non-Goals:**

- Redesigning the pending-exec artifact lifecycle.
- Changing the non-terminal refresh contract, the code-only refresh boundary, or the
  removed `--refresh-before-exec` behavior.
- Explaining the separately-observed intermittent flakes (launch-recovery endpoint
  resolution, CLI empty-response JSON parse). Those are recorded as follow-up candidates,
  not folded into this change.

## Decisions

### Decision 1: The suspected seam is refresh-settle vs pending-artifact durability

Two candidate owners, mutually exclusive:

- **Artifact durability**: the pending artifact is written with pre-reload offsets or is
  left behind in a shape the post-reload lookup treats as malformed, so `missing` is
  produced by the artifact-lifecycle rules correctly.
- **Recovery path**: the artifact survives and is resolvable, but the resubmit gate
  (`_running_or_timed_out_response`) never treats a post-reload continuation as
  non-terminal, so nothing resubmits.

Task 1.3 must pick one with evidence. The fix differs sharply: durability means writing or
refreshing the artifact across the settle; recovery means extending the continuation path
to carry the request through the reload the CLI itself requested.

### Decision 2: Preserve `missing` for real expiry, fix only the reload case

`implement-pending-exec-artifact-lifecycle` deliberately treats expired/malformed
artifacts as non-recoverable `missing`. That contract stays. The fix must make the
refresh-triggered reload distinguishable from genuine expiry, so the change does not
degrade the caller-visible signal into a blanket resubmit.

### Decision 3: Provisional spec delta, revised on evidence

The delta adds an explicit scenario to the existing requirement without changing its
normative text, matching the `diagnose-exec-endpoint-misroute` precedent. If task 1.3
shows the requirement text itself needs different substance, the delta is revised before
tasks are finalized rather than left as a scenario that does not describe the fix.

## Risks / Trade-offs

**[Fixing it by resubmitting could double-execute a script with side effects]** → If the
recovery side owns the defect, a resubmit must be safe for a script that may already have
run before the reload tore the environment down. The pending artifact's phase and the
script's own idempotency markers are the tools to distinguish "never ran" from "may have
run"; the fix must not blindly re-run. Task 2.4 must state which invariant it preserves.

**[The unit layer may not reproduce a real domain reload]** → If the loss is only
reproducible against a live reload, coverage lands as a focused real-host assertion and
the unit layer covers the artifact metadata, not the reload itself. Task 2.2 accepts this
explicitly rather than mocking a reload that behaves unlike the real one.
