## Context

Follow-up to `2026-10-13-make-base-url-exec-refresh-recoverable`, whose closeout recorded this
as a `validation-gap` candidate.

The Editor's change signal only watches compile-triggering code files. `_write_compile_triggering_probe`
in `tests/test_real_host_integration.py` accepts the caller's file name and appends it verbatim,
so a probe authored without its `.cs` suffix is written successfully and stages as
`no_pending_change`. The resulting failure — "change signal did not become pending" — points at
the change signal rather than at the probe name, and it costs a full Editor launch per attempt.

All seven current call sites pass an explicit `.cs` suffix, so the helper has never been
exercised with a bare name; that is why the gap survived the several refresh cases already in
the suite.

## Goals / Non-Goals

**Goals:**

- A mistyped real-host probe fails locally, immediately, and names the watched extensions.
- A change signal that never becomes pending reports enough for a reader to tell a mistyped probe
  from a genuine detection failure.
- No second, drifting list of watched extensions.

**Non-Goals:**

- Changing what the Editor watches. This is a test-harness fix; the product's refresh trigger set
  is durable and already documented.
- Changing any real-host case's behavior. Every current call site already stages a watched
  extension.
- Any product code change. Nothing the CLI emits is affected.
- The `product-improvement` candidate from the same closeout, tracked in
  `restore-base-url-exec-continuation-guidance`.

## Decisions

### Decision 1: Validate at staging time, not at wait time

The cheapest place to prevent the failure is where it is introduced — before the file is written
and long before an Editor launch. A wait-time check would still cost the launch.

### Decision 2: Derive the watched set, do not restate it

The watched extensions are already stated in durable help (`.cs`, `.asmdef`, `.asmref`, `.rsp`)
under "Help states that only code changes trigger automatic refresh". The helper reads them from
that source rather than repeating the list inline, so the two cannot drift. If that help entry is
ever reworded, the helper fails loudly at the point of staging rather than silently accepting a
name the Editor ignores.

### Decision 3: Improve the wait message too, but keep the two failures distinct

A correctly staged probe can still go unobserved if the Editor's poll interval outruns the wait,
so the wait helper's message is worth improving on its own. It must keep reporting a dropped
control endpoint as a *different* condition from a change signal that never became pending —
the existing message for that case already says so, and collapsing the two would reintroduce a
misdiagnosis in the opposite direction.

## Risks / Trade-offs

**[Deriving the set from prose couples a test helper to help text]** → Accepted: the coupling is
one-directional and fails loudly. A hardcoded list would drift silently, which is the failure
this change exists to remove.

**[Rejecting a name could break an existing call site]** → All seven pass `.cs`; verified by
running the real-host suite, which is the only layer that exercises these helpers anyway.

**[The staging rejection is not unit-covered]** → The helpers live in the real-host module, so the
rejection is verified by running that suite rather than by a mocked unit case.