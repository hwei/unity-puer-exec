## Context

Follow-up to `2026-10-13-make-base-url-exec-refresh-recoverable`, whose closeout recorded this
as a `product-improvement` candidate. That change made continuation candidates conditional: a
`wait-for-exec --request-id` candidate is marked `requires_replayable_record` and dropped when
the CLI holds no replayable record. That is correct for a request the service never accepted,
but it is stricter than the situation requires for an *accepted* one.

`_has_replayable_record` answers the question from selector context — "is a `project_path`
present?" — rather than from whether the addressed service holds a record for the request.
Because the `("exec", "running")` `wait-for-exec` candidate has a single `argv_template` naming
`--project-path`, a base-url `exec` returning `running` lost the candidate entirely, even
though `wait-for-exec --base-url --request-id` would answer that request correctly.

The change also puts the durable text in tension with itself. `runtime-guidance` says candidate
presence is determined by command and status alone; `formal-cli-contract` (from the archived
change) says a `request_id` continuation is offered only when a record exists.

## Goals / Non-Goals

**Goals:**

- A base-url `exec` that returns `running` for an accepted request advertises the continuation
  that actually works, with a usable `argv`.
- One answer in the durable text for when a continuation candidate may be absent.

**Non-Goals:**

- Changing `refresh_unsettled`, the settle budget, the resubmit path, or `missing`. All settled by
  `2026-10-13-make-base-url-exec-refresh-recoverable`.
- Making `wait-for-exec --request-id` work for a request the service never accepted. That is the
  `refresh_unsettled` contract, not a guidance gap.
- The real-host refresh-trigger staging gap, tracked in
  `validate-real-host-refresh-trigger-extension`.
- Changing the pending-exec artifact lifecycle or its retention rules.

## Decisions

### Decision 1: Presence follows the record; `argv` follows the context

The resolution of the text conflict. A continuation candidate that addresses a specific
`request_id` on the addressed service is a *reachability* question, answered by whether the
service holds a record. Every other candidate's presence follows command and status alone, and
its `argv` follows context. So:

- accepted project-path request → candidate with a `--project-path` argv (today's behavior)
- accepted base-url request → candidate with a `--base-url` argv (the fix)
- unaccepted request (`refresh_unsettled`) → no candidate (today's behavior, now durable text)

The implementation adds a `--base-url` `argv_template` alongside the existing one and selects
between them on the selector. A template whose selector is absent from context renders no
`argv` while the candidate stays, which is what the existing `log_range` rule already requires.

### Decision 2: Read record presence from the payload, not from a new transport call

`_has_replayable_record` must stop inferring the answer from the selector. The payload is the
right place to read it from: a `refresh_unsettled` response states `record_replayable: false`,
and an accepted response reached the server's accept path. Asking the service would mean an
extra round trip on the exec hot path to learn something the response already determines.

The selection stays scoped to statuses that already carry a `wait-for-exec` candidate.
`busy` names a *different* request than the one the caller owns and carries no such candidate
today, so it is unaffected.

### Decision 3: `requires_replayable_record` keeps its name and gains a defined meaning

The mark now means "the addressed service must hold a record for this `request_id`", not "the
CLI holds a replayable artifact". The name is kept because it still describes the condition
correctly; the design doc of the archived change used the narrower meaning, which is what made
the base-url case look accidental.

## Risks / Trade-offs

**[Two templates for one candidate can drift]** → The `when` string is the only other field, and
both variants render from it. A unit assertion that both variants render the same `when` and
differ only in the selector pins it.

**[Reading record presence from the payload could be wrong for a response the CLI did not
compose]** → The condition is only consulted for statuses that carry the candidate today, and
`record_replayable` is a CLI-composed envelope field, never a script-authored result field — the
same discriminator already used for `compile_blocked` and `refresh`.

**[Relaxing the drop rule could resurrect the original defect]** → The regression is that
`refresh_unsettled` still advertises no `wait-for-exec`. Both directions are asserted on the
caller-visible response, so the fix cannot be made by simply removing the rule.

**[A durable requirement is being amended]** → `runtime-guidance`'s "Incomplete log_range drops
argv but keeps the candidate" is MODIFIED, not replaced: the `log_range` rule stands unchanged
for every candidate that does not address a request record, and the exception is stated in the
requirement text itself.