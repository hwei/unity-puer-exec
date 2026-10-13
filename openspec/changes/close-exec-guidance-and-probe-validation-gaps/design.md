## Context

Follow-up to `2026-10-13-make-base-url-exec-refresh-recoverable`, whose closeout recorded two
candidates. Both were observed while applying that change, and neither is a regression of it.

- The `validation-gap` candidate was hit while writing the new real-host case: the probe was
  authored as `BaseUrlRefreshContinuationProbe` (no extension), so the Editor reported
  `skipped_reason: no_pending_change` and the case failed with "refresh did not trigger". The
  existing real-host refresh cases all pass an explicit `.cs` suffix, so the helper never had to
  cope with the mistake; it simply had no way to catch it.
- The `product-improvement` candidate came from the archived change's own Decision 4: a
  `wait-for-exec --request-id` candidate is marked `requires_replayable_record` and dropped when
  no replayable record exists. That is correct for a request the service never accepted, but for
  an *accepted* base-url request the continuation works and the candidate is dropped only because
  the single `argv_template` names `--project-path`.

The second candidate also exposes a text conflict. `runtime-guidance`'s "Incomplete log_range
drops argv but keeps the candidate" says candidate presence is determined by command and status
alone, and that a candidate missing selector context loses `argv` rather than being removed.
`formal-cli-contract` now says a `wait-for-exec --request-id` candidate is offered only when a
replayable record exists. Both are defensible; they differ on whether *reachability* is a
presence condition. This change resolves that in the durable text rather than leaving two
requirements that read as contradictions.

## Goals / Non-Goals

**Goals:**

- A mistyped real-host probe fails locally, immediately, and with the watched extensions named.
- A base-url `exec` that returns `running` for an accepted request advertises the continuation
  that actually works, with a usable `argv`.
- The two durable requirements agree on when a continuation candidate may be absent.

**Non-Goals:**

- Changing `refresh_unsettled`, the settle budget, the resubmit path, or `missing`. All settled by
  `2026-10-13-make-base-url-exec-refresh-recoverable`.
- Making `wait-for-exec --request-id` work for a request the service never accepted. That is the
  `refresh_unsettled` contract, not a guidance gap.
- The intermittent launch-recovery and CLI empty-response flakes, which have their own changes.
- Changing the pending-exec artifact lifecycle or its retention rules.

## Decisions

### Decision 1: Validate the probe name at staging time, not at wait time

The failure is cheapest to prevent where it is introduced — `_write_compile_triggering_probe`,
before the file is written and long before an Editor launch. The watched set is taken from what
the durable help already documents (`.cs`, `.asmdef`, `.asmref`, `.rsp`) rather than
reintroduced as a second list, so the two cannot drift. The wait helper still improves its
failure message, because the Editor's own poll timing can also leave a correctly staged probe
unobserved, and a reader of that failure needs to know what was watched.

### Decision 2: Presence follows the record; `argv` follows the context

The resolution of the text conflict: a continuation candidate that addresses a specific
`request_id` on the addressed service is a *reachability* question, answered by whether the
service holds a record. Every other candidate's presence follows command and status alone, and
its `argv` follows context. So:

- accepted project-path request → candidate with `--project-path` argv (today's behavior)
- accepted base-url request → candidate with `--base-url` argv (the fix)
- unaccepted request (`refresh_unsettled`) → no candidate (today's behavior, now durable text)

The implementation adds a `--base-url` `argv_template` alongside the existing one and selects
between them on the selector. A template whose selector is absent from context renders no
`argv` while the candidate stays, which is what the existing `log_range` rule already requires.

### Decision 3: `requires_replayable_record` keeps its meaning

The mark is now "the service must hold a record", not "the CLI must hold a replayable artifact".
`_has_replayable_record` currently answers it from selector context, which is why the accepted
base-url case was dropped; it must instead answer it from whether a record exists. The
`refresh_unsettled` payload already states `record_replayable: false`, and an accepted response
states the request was accepted — the payload is the right place to read the answer from, so no
extra transport call is introduced on the exec hot path.

## Risks / Trade-offs

**[Two templates for one candidate can drift]** → The `when` string is the only other field, and
both variants render from it. A unit assertion that both variants render the same `when` and
differ only in the selector pins it.

**[Reading record presence from the payload could be wrong for a `busy` response]** → `busy`
names a different request than the one the caller owns, and it carries no `wait-for-exec`
candidate today. The selection is limited to statuses that already carry one.

**[Validating probe names could break an existing real-host case]** → Every current call site
passes an explicit `.cs` suffix; the change is verified by running the real-host suite, not by
asserting it in the unit layer.

## Open Questions

- Whether `wait-for-exec --base-url --request-id` should also become the documented continuation
  in `exec --help-status` prose. The help already describes the status shapes; this change keeps
  prose untouched unless a scenario shows it contradicting the restored candidate.