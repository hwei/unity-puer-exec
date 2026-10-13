## Context

Continues `2026-09-21-diagnose-exec-missing-after-auto-refresh`. That change fixed the
deterministic cause (the settle budget was `--wait-timeout-ms`, so a 1.0 s window could never
cover a compile+reload) and explicitly left the `missing` classification and the branch
structure intact: "the fix does not simply silence `missing` for all requests". Its closeout
recorded this change as the `product-improvement` candidate that remained.

Verified state on current code. A base-url `exec` whose settle never returns ready emits:

```
exit 10, status "running", phase "refreshing", request_id R
next_steps: [{command: "wait-for-exec",
              when: "you want to continue waiting for the accepted request to finish"}]
```

and `wait-for-exec --base-url --request-id R` then answers exit 13 / `missing`
(`no recoverable record exists for request_id`). The response advertises an *accepted*
request that the server never accepted: `HandleExecAsync` returns the refreshing phase before
`TryAcceptExecRequest`, and base-url mode keeps no client-side record.

## Goals / Non-Goals

**Goals:**

- Make the documented continuation for a base-url request actually converge on the script
  result, or stop advertising a continuation that cannot.
- Keep `missing` meaning what it means: the addressed service has no recoverable record.
- Preserve the accepted-job lifecycle: no resubmit of a request that may already have run.

- Make the two budgets distinguishable from the help alone: the per-request wait a caller
  chooses, and the compile-scale budget the CLI settles a refresh on.

**Non-Goals:**

- Re-litigating the settle budget, the server's refresh decision, or the non-terminal refresh
  contract itself (settled by the previous change).
- Redesigning the pending-exec artifact lifecycle for project-path mode.
- The intermittent launch-recovery and CLI empty-response flakes, which have their own
  changes.
- A caller-facing settle-budget knob on `exec`. `wait-for-compile` has
  `--settle-timeout-seconds`; adding one to `exec` would let a caller make the very mistake the
  help statement documents. If the investigation finds a reason to want one, it is recorded as
  a follow-up candidate.

## Decisions

### Decision 1 (inventory): the branches that hand back a request nobody holds

Verified against the current code and against the server source. Three base-url branches in
`_run_exec_impl` returned a non-terminal refreshing phase for a request that had no record
anywhere; all three emitted the identical `_emit_running_payload(...)` shape, which selects
`GUIDANCE_MATRIX[("exec", "running")]` — whose first candidate is
`wait-for-exec --project-path --request-id` under the `when` string "you want to continue
waiting for the **accepted** request to finish".

| # | Branch (call site) | Reachable? | What it returned before |
|---|--------------------|-----------|------------------------|
| A | `settled is None` — the settle-timeout branch: `_settle_after_automatic_refresh` returned `None` because `wait_for_compile_cycle` reported `settle_timeout` (refresh loop in `_run_exec_impl`) | Yes — the exact real-host failure | `EXIT_RUNNING`, `running`/`refreshing`, no resubmit |
| B | `refresh_attempts >= 1` — the single permitted resubmit was answered `refreshing` again (the server still sees a compile-triggering change) | Yes — whenever a script writes a `.cs` file on every exec | `EXIT_RUNNING`, `running`/`refreshing`, after one resubmit |
| C | post-settle resubmit answered `compiling` — `HandleExecAsync` answers `{"ok":false,"status":"compiling"}` from its `IsCompilingOrReloading()` guard, which runs *before* `TryAcceptExecRequest` | Yes — a compile that outlives the settle | passthrough `{"ok":false,"status":"compiling"}`, exit 11; project-path mode normalizes this to `running`, base-url mode did not |

`diagnose-exec-missing-after-auto-refresh` closed **branch A only**, and only for its
deterministic cause: it made the settle budget compile-scale
(`_post_refresh_ready_timeout_seconds`), so a 1.0 s `--wait-timeout-ms` no longer expires the
settle. It deliberately left the `missing` classification and the branch structure intact. B
and C are untouched by it, and A remains reachable whenever the budget is genuinely exceeded.

**The `request_id` in those responses has no record anywhere.** Server-side, `HandleExecAsync`
returns the refreshing phase before `TryAcceptExecRequest`, so no job exists. Client-side, every
`_write_pending_exec` / `_read_pending_exec` call in `_run_exec_impl` and
`_run_wait_for_exec_impl` is gated on `selector == "project_path"`, and `_run_wait_for_exec_impl`
takes its `else` branch (`pending = None`) for base-url, calling `wait-for-exec` on the service
directly. The service then answers `BuildSimpleErrorJson("missing", "no recoverable record
exists for request_id", ...)`. This was reproduced against the CLI with a mocked transport
(task 1.2): `exec --base-url` reached branch A and returned the refreshing payload above, and
the continuation advertised in that payload's `next_steps` was unrenderable.

### Decision 1 (chosen): neither candidate — stay non-terminal only while a continuation exists

Of the two candidates in the proposal:

- **In-process retry is already what ships.** `_run_exec_impl` settles the compile cycle and
  resubmits under the same `request_id`; `test_base_url_automatic_refresh_settles_cycle_longer_than_wait_timeout`
  proves a cycle longer than `--wait-timeout-ms` still converges on the script result. So the
  delta spec's "either keeps resubmitting the request until the script runs or reports a
  terminal outcome naming the exhausted budget" is satisfied by the existing retry across the
  whole budget, and by the terminal outcome for whatever is left.
- **A client-side base-url record was rejected with evidence.** It would make the advertised
  `wait-for-exec --request-id` literally true, but it adds a CLI-owned persistence surface — a
  home, a key, a retention bound, and a sweep — to serve only requests that are, by
  construction, *still unaccepted and never ran*.
  `diagnose-exec-missing-after-auto-refresh` established that such a record is never absent for
  that reason; it would be a replay surface with no server-side counterpart that can disagree
  with the server. It also does nothing for branches B and C, which are not about losing a
  record but about never having one.

So the fix is: **a base-url exec reports a non-terminal refreshing phase only while a
continuation can actually converge; when it cannot, it reports a terminal state that names the
exhaustion and the resubmit path.** The advertised `next_steps` do change — the
`("exec", "refresh_unsettled")` guidance offers `exec` (resubmit) and `wait-for-compile`
(observe the cycle), never `wait-for-exec`.

### Decision 2 (resolved): `refresh_unsettled`, exit 25, resubmit-safe

A new non-success status `refresh_unsettled`, exit code **25** (unused in the baseline model;
`missing` stays 13), carrying:

- `reason`: `refresh_settle_timeout` (A), `refresh_persisted` (B), `compile_in_progress` (C);
- `record_replayable: false` — there is nothing to continue;
- `resubmit_safe: true` and `recoverable: true` — this is not a lost request;
- `next_steps`: resubmit the same `exec`, optionally after `wait-for-compile`.

**Resubmit-safety invariant.** In all three branches the server answered *before*
`TryAcceptExecRequest`: A and B from the pre-acceptance refresh gate, C from the
`IsCompilingOrReloading()` guard. No `execJob` was ever created, so the script has not run, and
re-submitting the same `request_id` with equivalent content runs it for the first time. It is
recorded in the payload as `resubmit_safe` and asserted by the regressions, so a future change
that let one of these branches follow an acceptance would break a test rather than silently
double-run a script.

### Decision 3 (resolved): `missing` keeps its meaning

`missing` is untouched: `_run_wait_for_exec_impl` still forwards a base-url `wait-for-exec`
straight to the service and returns whatever it says, and a genuinely absent or expired pending
artifact still reads `None` and takes that same path. Only the three branches where the CLI
itself held an unaccepted request changed shape.
`test_project_path_refresh_still_reports_running_with_replayable_guidance` guards the opposite
direction — the replayable project-path branch must keep `running` *and* its
`wait-for-exec --project-path --request-id` candidate.

### Decision 4 (resolved): the unreachable-continuation rule, and help states the budget's nature

Two separate surfaces:

1. **Guidance.** A `wait-for-exec --request-id` candidate is marked
   `requires_replayable_record`; the renderer drops it when the addressed service holds no
   replayable record (a base-url exec, or a payload with `record_replayable: false`). It was
   already unrenderable in base-url mode — its `argv_template` needs `{project_path}` — but it
   still surfaced as a bare `command`/`when` pair describing an *accepted* request, which is the
   defect. The other `running` candidates (`wait-for-result-marker`, `wait-for-log-pattern`)
   need no such record and are unaffected.
2. **Help.** `exec --help` states, in the `--wait-timeout-ms` option line, the "Automatic
   refresh" line, and **Timeout Rules**, that the settle runs on a compile-scale budget of its
   own and is not bounded by `--wait-timeout-ms`, naming `wait-for-compile
   --settle-timeout-seconds` as the same cycle. No literal number, so the prose cannot drift
   from `unity_session.DEFAULT_READY_TIMEOUT_SECONDS`. `exec --help-status` repeats the fact next
   to the `refresh_unsettled` entry; `wait-for-compile --help` already describes the same cycle
   and is unchanged.

## Risks / Trade-offs

**[Blocking longer on a stuck refresh is a worse failure mode than returning early]** → Not
taken up: the in-process retry already ships on the budget
`diagnose-exec-missing-after-auto-refresh` established. The remaining exposure is a caller who
picked a `--wait-timeout-ms` in the seconds while the refresh wanted minutes; the honest terminal
outcome plus the resubmit path bounds it, and help now says so up front.

**[A client-side base-url record is a new persistence surface]** → Rejected, with reasoning, in
Decision 1. Recorded as the alternative should a future caller-visible need appear.

**[A new help line weakens an existing help assertion]** → No pre-existing assertion was changed
or relaxed. The strings that moved (`--wait-timeout-ms`, the "Automatic refresh" line) were
re-read after the edit: the substring guarantees in `test_exec_help_args_renders_argument_template`
("Automatic refresh: before each exec the server checks", "not watched and do not trigger a
refresh") still hold, and `test_exec_help_args_renders_argument_template` /
`test_exec_help_status_includes_unity_compile_error` were extended, not replaced.

**[A new exit code is a machine-contract change]** → 25 is documented in `exec --help-status`,
distinguished from `missing` in prose, and pinned by
`test_exec_refresh_unsettled_help_distinguishes_itself_from_missing`.

**[The unit layer may not reproduce the real ordering]** → The clock-modelled settle harness
expresses the budget arithmetic deterministically. Task 4.3 confirms on the host.