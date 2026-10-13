## Why

The closeout of `2026-10-13-make-base-url-exec-refresh-recoverable` recorded a
`product-improvement` candidate: `exec --base-url` returning `running` for an accepted request
advertises no `wait-for-exec` continuation, even though `wait-for-exec --base-url --request-id`
would work for that request. The candidate is dropped only because its single `argv_template`
names `--project-path`, which base-url mode does not have.

That change also left the durable text self-contradictory. It added a rule to
`formal-cli-contract` — offer `wait-for-exec --request-id` only when the addressed service holds
a record — while `runtime-guidance`'s "Incomplete log_range drops argv but keeps the candidate"
says candidate presence is determined by command and status alone, and that a candidate with
incomplete context loses its `argv` rather than being removed. Both are defensible; they differ
on whether *reachability* is a presence condition. That question needs one answer in the durable
text, not two.

## What Changes

- Add a `--base-url` variant of the `("exec", "running")` `wait-for-exec` candidate and select
  between the two variants on the selector, so a base-url `exec` that returns `running` for an
  accepted request advertises the continuation that actually works, with a usable `argv`.
- Re-express `requires_replayable_record` as *record presence* rather than *template
  fillability*: presence follows whether the addressed service holds a record for the
  `request_id`, and `argv` follows whether CLI-owned context can fill the template.
- Reconcile the two durable requirements so they agree: presence follows the record, `argv`
  follows the context. A request the service never accepted (`refresh_unsettled`) still offers
  no such candidate.
- Leave the real-host refresh-trigger staging gap recorded separately in
  `validate-real-host-refresh-trigger-extension`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `runtime-guidance`: adds a requirement that a `wait-for-exec --request-id` continuation
  requires a record on the addressed service rather than a fillable template — an accepted
  request keeps the candidate in either selector, with `argv` omitted when it cannot be filled —
  and amends "Incomplete log_range drops argv but keeps the candidate" so the two rules read as
  one.

## Impact

- Affected code: `cli/python/help_surface.py` (`GUIDANCE_MATRIX[("exec", "running")]`,
  `_render_next_steps`), `cli/python/unity_puer_exec_runtime.py` (`_build_guidance_context`,
  `_has_replayable_record`), `tests/test_unity_session_cli.py`.
- Affected behavior: which continuation candidates an `exec` response advertises, for both
  selectors. An accepted base-url `running` response gains a `wait-for-exec` candidate with a
  complete `--base-url` argv.
- Affected validation: unit-only. The change adds no real-host requirement, so it is verifiable
  in the default suite.
- No change to `refresh_unsettled`, the settle budget, the resubmit path, or `missing` — all
  settled by `2026-10-13-make-base-url-exec-refresh-recoverable`.
- Inherited findings: the accepted-base-url candidate gap was observed while applying
  `2026-10-13-make-base-url-exec-refresh-recoverable`; see that change's `design.md`
  Decision 4 and its closeout record.