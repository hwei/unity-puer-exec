## Why

`recover-peer-reset-transport-drop` was archived
(`2026-10-13-recover-peer-reset-transport-drop`) with **unit-level evidence only**. Its
recorded evidence is three mocked boundary tests plus two mocked play-path tests in
`tests/test_direct_exec_client.py` and `tests/test_unity_session_cli.py`. No live Editor was
involved.

The condition it fixes was discovered only in a real-host run. The originating failure
(`test_play_settles_a_pending_change_then_reaches_playing`, archived change
`2026-10-13-validate-real-host-refresh-trigger-extension`) was a single occurrence of a
`[WinError 10054]` during a live play transition. That is the only observation of the real
condition, and it was a *failure* observation, not a confirmation of the fix.

The archived reproduction `repro_play_transport_reset.py` proved the mechanism deterministically
by monkeypatching the transport in-process. It never opened a socket to a real Editor. So the
fix is verified against a *simulated* `RemoteDisconnected`, not against the one that actually
occurs — the CPython behavior that produces it is version- and platform-specific, and this
machine is Windows with a particular interpreter build.

There is also a coverage gap the change left open. The new boundary catch admits `OSError`
broadly (design "Risks / Trade-offs" flagged this). A mocked test can prove that a constructed
`RemoteDisconnected` is classified correctly. It cannot prove that the *real* Editor's reset
produces the same classification, nor that the catch does not now swallow a condition that
should have surfaced differently on a live endpoint.

## What Changes

- Run the real-host suite against the validation host and record whether the play path still
  reaches `playing` without an opaque `status: "failed"`.
- Capture a real transport-reset transcript from a live Editor if one occurs during the run,
  and confirm the reported payload names it as `not_available` with the reset detail visible.
- Confirm the broadened `OSError` catch does not mask a distinct live condition — specifically
  that no real-host case now reports `not_available` where it previously reported a specific,
  more actionable state.
- Record the evidence as `host-validation` on this change's `meta.yaml` when a real run
  completes, so the archive records what the unit tests cannot.

### What this change explicitly does not do

It does not attempt to *induce* a peer reset on demand. A reset is a timing race on a live
socket during a domain reload; staging it deterministically would require the transport-level
control that does not exist today. This change validates the fix against the real endpoint as
far as a normal real-host run reaches, and records honestly when a reset did not occur — a run
with no reset is "no regression observed", not "the reset path is confirmed".

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