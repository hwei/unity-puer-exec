# Design

## Context

See `proposal.md` — Why. The two settle paths as they stand:

- `_settle_after_automatic_refresh(args, selector, session, base_url, recovery)` branches on the
  selector. Project-path returns `_ensure_project_session_ready_after_refresh(args)`, which is
  `unity_session.ensure_session_ready(..., ready_timeout_seconds=_post_refresh_ready_timeout_seconds(args))`.
  Base-url returns `_settle_base_url_after_refresh(base_url, args, recovery)`, which is
  `wait_for_compile_cycle(base_url, appear, settle, health)` with
  `appear = args.appear_timeout_seconds or DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS` (10 s) and
  `settle = _post_refresh_ready_timeout_seconds(args)` (180 s).
- Only the base-url branch treats `COMPILE_OUTCOME_TIMEOUT` as "still in flight" and returns `None`;
  the project-path branch returns `None` only on `UnityStalledError` / `UnityNotReadyError`.
- The exec loop permits one resubmit (`refresh_attempts >= 1`), then reports the non-terminal
  `refreshing` phase for project-path and `refresh_unsettled` for base-url.

Inherited findings that remain true: the host's bounded age is 8 s and is asserted to stay under
the CLI's 10 s appear window (`tests/test_refresh_change_signal.py::test_grace_is_shorter_than_the_cli_compile_appear_window`);
the settle budget is compile-scale and deliberately not `--wait-timeout-ms`
(`2026-09-21-diagnose-exec-missing-after-auto-refresh`). The gap is that project-path mode never
spends the appear window, so the invariant "a caller that waits out its appear window re-asks after
the host has acknowledged" holds for one selector only.

## Goals / Non-Goals

**Goals:**

- One `exec --project-path` invocation reaches a terminal result for a refresh the host resolves
  without compiling, matching base-url `exec` and `play`.
- Both selectors spend the same appear and settle budgets on the same compile cycle, so the
  host-side bounded age has one meaning rather than one per selector.
- The re-resolved endpoint a domain reload produces is still what the compile wait polls.

**Non-Goals:**

- No host change. The bounded age, the ledger, and its gates stay as landed.
- No change to `--wait-timeout-ms` semantics or to the compile-scale settle budget.
- No change to the one-permitted-resubmit rule, to `refresh_unsettled`, or to the continuation
  guidance. Those remain the exhaustion path; this change makes exhaustion rarer, not different.
- Not adding ScriptUpdater auto-decline or `unity_pid` watching to the project-path settle. Parity
  with the base-url call is the goal; a richer wait is a separate question.

## Decisions

### D1. Compose the two primitives rather than parameterize `ensure_session_ready`

Project-path mode needs `ensure_session_ready` for what only it does: resolve or launch the Editor,
validate project identity, and re-resolve the published endpoint across the domain reload a real
compile ends with. `wait_for_compile_cycle` needs a base URL to poll. So the settle becomes
`ensure_session_ready` **then** `wait_for_compile_cycle` on the session's resolved `base_url`,
rather than teaching `ensure_session_ready` an appear window it otherwise has no use for.

The alternative — an `appear_timeout_seconds` parameter on `ensure_session_ready` — was rejected
because that function is the shared readiness entry for every project-scoped command, and an
appear window is only meaningful immediately after a refresh dispatch. Threading it through the
shared path would make every caller reason about a compile edge it did not cause.

### D2. Ordering: readiness first, then the compile edge

Readiness must come first because a domain reload can rebind the control port; polling a stale
`base_url` for a compile edge would read a dropped endpoint as the reload edge `wait_for_compile_cycle`
already interprets that way, and confuse a genuine cross-reload settle with a transport failure.
After `ensure_session_ready` returns, the session's `base_url` is the resolved one, so the compile
wait observes the endpoint that will answer the resubmit.

### D3. Budgets stay the base-url budgets, and the timeout outcome stays "still in flight"

The appear window comes from `args.appear_timeout_seconds` with the same
`DEFAULT_COMPILE_APPEAR_TIMEOUT_SECONDS` fallback; the settle budget stays
`_post_refresh_ready_timeout_seconds(args)`. `COMPILE_OUTCOME_TIMEOUT` returns `None` on the
project-path branch too, so an unfinished cycle reports the non-terminal `refreshing` phase exactly
as it does today rather than being mistaken for a settled one.

Total worst case for a project-path `exec` whose refresh compiles nothing becomes
readiness + appear window instead of readiness alone. That is the intended cost: it buys a terminal
result in one invocation, and it is the cost base-url mode already pays.

### D4. The host's bounded age is not retuned

With both selectors spending the appear window, the 8 s age sits inside a 10 s wait for every
caller, which is the relationship the existing invariant test asserts. Widening the age would
weaken the D7 gates that keep a failing build from being suppressed; narrowing it would re-open
the race those gates close. Neither is needed once the caller waits.

### D5. Capture a compile-generation baseline before readiness

The host advances `compile_generation` on `compilationFinished` and persists it across the domain
reload through `SessionState`. The project-path settle therefore probes `/health` on the pre-settle
`base_url` **before** calling `ensure_session_ready`, and passes the generation it read as
`compile_generation_baseline` to `wait_for_compile_cycle`. A compile that finished while readiness
was being awaited then shows as `generation > baseline` and settles immediately as
`generation_advance`; a refresh that compiled nothing leaves the generation unchanged, so the wait
spends the appear window exactly as base-url mode does.

If that pre-readiness probe fails (endpoint already down for a reload) or the payload carries no
generation, the baseline is `None` and the wait falls back to the plain appear window. That
fallback costs at most the appear window and never settles early, so it is the safe direction.
The base-url branch is deliberately left without a baseline: it does not ride out readiness first,
so it sees `compiling` directly.

## Risks / Trade-offs

- **[A project-path `exec` with no compile now takes ~10 s longer]** → It also stops returning a
  non-terminal phase that needs a second invocation, so the wall-clock to a script result is lower,
  not higher. A caller that genuinely wants the old behaviour can use `--base-url`, which already
  waits.
- **[Double-waiting when `ensure_session_ready` already rode out the compile]** →
  `wait_for_compile_cycle` only short-circuits an already-`ready` endpoint when it is given a
  `compile_generation_baseline` (see D5); without one, a genuine `.cs` change whose compile and
  reload finished inside `ensure_session_ready` would spend the full appear window and end as
  `no_compile_observed`. With the baseline, the cost is one health probe, not a second window.
- **[A reload between readiness and the compile wait drops the endpoint]** →
  `wait_for_compile_cycle` already treats a previously-ready endpoint dropping as a reload edge and
  keeps waiting; the resubmit re-resolves through the normal project-path path.
- **[The two branches drift again]** → The mocked case asserts the project-path settle calls the
  same compile-wait primitive with the same budgets, so a future edit that drops it fails a test
  rather than silently re-introducing the two-invocation behaviour.

## Migration Plan

CLI-only, in the published package's `CLI~` executable and the repository's Python entry. No state
to migrate. An older CLI against a newer host keeps working: it just needs the second invocation
this change removes. Rollback is reverting the composition, which restores today's behaviour
exactly because nothing on the host depends on it.
