# validate-peer-reset-recovery-against-real-host

> ## Outcome — read this before quoting this change as evidence
>
> **A real host was exercised. The reset path was NOT confirmed.**
>
> The run completed: 42 tests, OK (skipped=3), 2126.888s, Unity 2022.3.62f2 against the
> prepared validation host. All six play-mode cases ran and passed, including
> `test_play_settles_a_pending_change_then_reaches_playing` — the case that originally
> produced `[WinError 10054]`.
>
> **What this retires:** one risk the archived `recover-peer-reset-transport-drop` flagged for
> itself. Over 35 minutes with three host-relaunch boundaries, two control-port rollovers and
> several domain reloads, nothing surfaced as an unattributed `not_available`. That is the one
> class of result a mocked test structurally cannot produce.
>
> **What this does not establish:** no peer reset occurred during the run, so the live payload
> shape (`not_available` / exit 12 / errno in `error` / `transport_detail.reason`) was never
> observed on a live endpoint. The classification still rests on a constructed
> `RemoteDisconnected` in `tests/test_direct_exec_client.py`. The originating failure was a
> single occurrence across a real-host run; a clean run that reproduces no reset is **"no
> regression observed"**, not **"the reset path is confirmed"**. Do not quote the two
> interchangeably.
>
> `real-host-run.md` carries the full claim-by-claim table. `meta.yaml` deliberately retains
> `tests` alongside `host-validation` so this record does not read as live-confirmed.

## Why

`recover-peer-reset-transport-drop` was archived
(`2026-10-13-recover-peer-reset-transport-drop`) with **unit-level evidence only** — three
mocked boundary tests plus two mocked play-path tests. No live Editor was involved. Its
archived reproduction proved the mechanism by monkeypatching the transport in-process; it never
opened a socket to a real Editor, and the CPython behavior that produces the reset is version-
and platform-specific.

The condition was discovered only in a real-host run. The originating failure
(`test_play_settles_a_pending_change_then_reaches_playing`, archived change
`2026-10-13-validate-real-host-refresh-trigger-extension`) was a single occurrence of a
`[WinError 10054]` during a live play transition — a *failure* observation, never a
confirmation.

The archived change also left a gap it named itself: the boundary catch admits `OSError`
broadly (design "Risks / Trade-offs"). A mocked test proves a constructed
`RemoteDisconnected` maps correctly. It cannot prove the real Editor's reset produces the same
classification, nor that the catch does not swallow a live condition that should have surfaced
differently.

## What Changes

- Run the real-host suite against the validation host and record whether the play path still
  reaches `playing` without an opaque `status: "failed"`.
- Capture a real transport-reset transcript from a live Editor if one occurs, and confirm the
  reported payload names it as `not_available` with the reset detail visible.
- Confirm the broadened `OSError` catch does not mask a distinct live condition — specifically
  that no real-host case now reports `not_available` where it previously reported a specific,
  more actionable state.
- Record the evidence actually obtained on this change's `meta.yaml`, so the archive records
  what the unit tests cannot.

### What this change explicitly does not do

It does not attempt to *induce* a peer reset on demand. A reset is a timing race on a live
socket during a domain reload; staging it deterministically would require transport-level control
that does not exist today. This change validates the fix against the real endpoint as far as a
normal real-host run reaches, and records honestly when a reset did not occur.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none)

No spec delta: this is validation of behavior `play-mode-control` already specifies. The
interesting artifact is the recorded evidence, not a new requirement. `.openspec.yaml` sets
`skip_specs: true`.

## Impact

- Affected code: none expected. If a real-host failure reveals the fix is incomplete, that is a
  finding for a follow-up change, not a silent widening of scope here.
- Affected validation: `tests/test_real_host_integration.py`, run against the validation host.
- Prerequisite: the real-host gate must be enabled and a prepared host available. When those
  are absent the run skips, and a skip must be recorded as a skip rather than as evidence.