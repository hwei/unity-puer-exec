## Context

The unit evidence for the archived fix is deterministic and strong *about the mapping*: a
constructed `http.client.RemoteDisconnected(ConnectionResetError(10054, ...))` is proven to
become `not_available` / exit 12 with the errno preserved. The archived reproduction
(`openspec/changes/archive/2026-10-13-reproduce-play-mode-transport-reset-flake/repro_play_transport_reset.py`)
established the mechanism the same way — by monkeypatching the transport, never by opening a
socket to a real Editor.

That is a deliberate and appropriate division: the mechanism is Python's, so it can be pinned
without an Editor. What it cannot establish is whether the real Editor's reset is the same
shape of event, and whether catching `OSError` broadly hides anything live.

## Goals / Non-Goals

**Goals:**

- Validate the fix against a live Editor on the validation host.
- Check the one risk the mocked tests structurally cannot check: a live condition that the
  broadened catch now silently reclassifies as `not_available`.

**Non-Goals:**

- Not inducing a peer reset deterministically. It is a timing race on a live socket during a
  domain reload; no control surface for staging it exists today.
- Not adding a reset-staging mechanism to the package. If that becomes worth doing, it is its
  own change with its own cost.
- Not re-litigating the classification. That was decided and is recorded in the archived change.

## Decisions

### Decision 1: A clean real-host run is "no regression observed", not "the reset path is confirmed"

This is the central honesty constraint of the change. A reset is rare — the original failure was
a single occurrence across a real-host run. A green run therefore says almost nothing about the
reset path specifically. The change must record which of the two it actually achieved.

Collapsing these into one "validated" claim would recreate the exact failure mode the
investigation had to undo: a condition whose evidence is weaker than its confidence.

### Decision 2: The `OSError` breadth check is a real-host task, not a mock task

A mocked test can enumerate exception classes and assert each maps somewhere sensible — the
archived change does that. It cannot enumerate *live* conditions. A real host may produce an
`OSError` for a reason the classification does not anticipate, and the only place that becomes
visible is a real run. Hence task 2.1 is scoped to attributing every `not_available` seen live.

### Decision 3: No spec delta

`play-mode-control` already specifies the recovered behavior. This change either confirms it
against reality or produces a finding. It does not itself add a requirement.

## Risks / Trade-offs

**The run may not reproduce the condition** → the change can end with weaker evidence than it
set out to gather. That is an acceptable and honest outcome; Decision 1 exists to make it
reportable rather than to prevent it.

**Prerequisites may be absent** → the suite skips silently by design. A silent skip read as a
pass is precisely the failure the validation spec's result-interpretation table warns about, so
task 1.1 requires stating each prerequisite's observed value before any claim is made.