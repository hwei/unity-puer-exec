## Why

The closeout of `2026-10-13-make-base-url-exec-refresh-recoverable` recorded two follow-up
candidates: a real-host validation gap that cost debugging time, and a guidance rule now in
tension with an existing requirement.

First, `_write_compile_triggering_probe` accepts the caller's file name unvalidated, and the
Editor only watches compile-triggering code files. A probe authored without its `.cs` extension
staged as `no_pending_change`, so a real-host case failed with "refresh did not trigger" — a
symptom three steps from the cause, at a full Editor launch per attempt.

Second, that change made continuation candidates conditional on a replayable record. Correct for
an unaccepted request, but stricter than needed for an *accepted* one:
`wait-for-exec --base-url --request-id` works there, dropped only because the template needs
`--project-path`. `runtime-guidance` instead requires presence to follow command and status
alone, with an incomplete candidate losing `argv` but staying.

## What Changes

- `_write_compile_triggering_probe` validates that the probe name ends in a watched
  compile-triggering extension, and `_wait_for_refresh_pending` names the watched extensions
  and the actual `skipped_reason` when the change signal never becomes pending. A mistyped
  probe fails locally and immediately instead of after an Editor launch.
- Add a `--base-url` variant of the `("exec", "running")` `wait-for-exec` candidate, so a
  base-url `exec` that returns `running` for an accepted request advertises the continuation
  that actually works.
- Reconcile the durable text: `runtime-guidance` states that candidate presence is determined
  by command and status alone, and `formal-cli-contract` states that a `wait-for-exec
  candidate` is offered only when a replayable record exists. The reconciliation distinguishes
  the two conditions — an *accepted* request with a server-side record keeps its candidate,
  with or without `argv`; a request the service never accepted offers no such candidate.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `validation-host-integration`: adds a requirement that a real-host refresh trigger is
  staged with a watched compile-triggering extension, and that a change signal which never
  becomes pending fails with the watched extensions and the observed `skipped_reason` named.
- `runtime-guidance`: adds a requirement that candidate *presence* for
  `wait-for-exec --request-id` depends on whether the addressed service holds a record for
  that `request_id` — an accepted request keeps the candidate in either selector, with `argv`
  omitted when the template cannot be filled — and amends the existing
  "candidate presence is determined by command and status alone" requirement so the two rules
  do not read as contradictions.

## Impact

- Affected code: `tests/test_real_host_integration.py`
  (`_write_compile_triggering_probe`, `_wait_for_refresh_pending`),
  `cli/python/help_surface.py` (`GUIDANCE_MATRIX[("exec", "running")]`,
  `_OPTIONAL_FORWARDED_ARGS`), `cli/python/unity_puer_exec_runtime.py`
  (`_build_guidance_context`, `_has_replayable_record`).
- Affected behavior: which continuation candidates a base-url `exec` response advertises when
  the request was accepted; the failure message of a mistyped real-host refresh probe.
- Affected specs: `runtime-guidance` (candidate presence) and `validation-host-integration`
  (refresh trigger staging). No change to `refresh_unsettled`, to the settle budget, or to
  `missing` — all settled by `2026-10-13-make-base-url-exec-refresh-recoverable`.
- Inherited findings: the probe-extension gap and the accepted-base-url candidate gap were both
  observed while applying `2026-10-13-make-base-url-exec-refresh-recoverable`; see that
  change's `design.md` Decisions 1 and 4 and its closeout record.